from __future__ import annotations
import os
import traceback
from typing import Tuple, List, Optional
import typing
from PyQt5.QtCore import QThread

from pwspy.analysis import AbstractAnalysisSettings, AbstractAnalysis
from pwspy.analysis._abstract import AbstractRuntimeAnalysisSettings
from pwspy.analysis.dynamics import DynamicsAnalysisSettings, DynamicsAnalysis
from pwspy.analysis.dynamics._analysisSettings import DynamicsRuntimeAnalysisSettings
from pwspy.analysis.pws._analysisSettings import PWSRuntimeAnalysisSettings
from pwspy.apps.PWSAnalysisApp._sharedWidgets import ScrollableMessageBox
from pwspy.apps.sharedWidgets.dialogs import BusyDialog
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox, QInputDialog
from pwspy.dataTypes import ImCube, CameraCorrection, ExtraReflectanceCube, AcqDir, ICMetaData
from pwspy.analysis.pws import PWSAnalysisSettings
from pwspy.analysis.pws import PWSAnalysis
from pwspy.analysis.warnings import AnalysisWarning
from pwspy.dataTypes._arrayClasses._ICBaseClass import ICRawBase
from pwspy.dataTypes._metadata._MetaDataBaseClass import AnalysisManagerMetaDataBase
from pwspy.utility.fileIO import loadAndProcess
import threading
from multiprocessing.util import Finalize
from multiprocessing.sharedctypes import RawArray
import numpy as np
if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.App import PWSApp

def safeCallback(func):
    """A decorator to make a function print its traceback without crashing."""
    def newFunc(*args):
        try:
            func(*args)
        except:
            traceback.print_exc()
    return newFunc


class AnalysisManager(QtCore.QObject):
    analysisDone = QtCore.pyqtSignal(str, AbstractAnalysisSettings, list)

    def __init__(self, app: PWSApp):
        super().__init__()
        self.app = app

    def runList(self):
        """Run multiple queued analyses as specified by the user."""
        for anName, anSettings, cellMetas, refMeta, camCorrection, widgetHandle in self.app.window.analysisSettings.getListedAnalyses():
            self.runSingle(anName, anSettings, cellMetas, refMeta, camCorrection)
            [cellItem.refresh() for cellMeta in cellMetas for cellItem in self.app.window.cellSelector.tableWidget.cellItems if cellMeta == cellItem.acqDir] #Refresh our displayed cell info
            _ = widgetHandle.listWidget().takeItem(widgetHandle.listWidget().row(widgetHandle)) #remove the analysis item once it has been run
            del _

    @safeCallback
    def runSingle(self, anName: str, anSettings: AbstractRuntimeAnalysisSettings, cellMetas: List[AcqDir], refMeta: AcqDir,
                  cameraCorrection: CameraCorrection) -> Tuple[str, AbstractAnalysisSettings, List[Tuple[List[AnalysisWarning], AcqDir]]]:
        """Run a single analysis batch"""
        userSpecifiedBinning: Optional[int] = None
        if isinstance(anSettings, PWSRuntimeAnalysisSettings):
            cellMetas = [i.pws for i in cellMetas]
            refMeta = refMeta.pws  # We are only interested in pws data here
        elif isinstance(anSettings, DynamicsRuntimeAnalysisSettings):
            cellMetas = [i.dynamics for i in cellMetas]
            refMeta = refMeta.dynamics
        if refMeta is None:
            raise ValueError(f"No measurement for analysis type {type(anSettings)} found in the reference cell.")
        cellMetas = [i for i in cellMetas if i is not None]  # Remove None items from the list of cells. This happens e.g. when you are analyzing dynamics but not all acqs have dynamics
        if len(cellMetas) == 0: return  # If all item were `None` then there is no point moving forward.
        #Determine which cells already have an analysis by this name and raise a deletion dialog.
        conflictCells = []
        for cell in cellMetas:
            if anName in cell.getAnalyses():
                conflictCells.append(cell)
        if len(conflictCells) > 0:
            ret = ScrollableMessageBox.question(self.app.window, "File Conflict", f"The following cells already have an analysis named {anName}. Do you want to delete existing analyses and continue?: \n {', '.join([os.path.split(i.acquisitionDirectory.filePath)[-1] for i in conflictCells])}")
            if ret == QMessageBox.Yes:
                [cell.removeAnalysis(anName) for cell in conflictCells]
            else:
                return
        if cameraCorrection is None:  # This means that the user has selected automatic cameraCorrection
            correctionsOk = self._checkAutoCorrectionConsistency(cellMetas + [refMeta])
        else:
            correctionsOk = True #We're using a user provided camera correction so we assume it's good to go.
        if correctionsOk:
            ref = refMeta.toDataClass()
            if cameraCorrection is not None:
                try:
                    ref.correctCameraEffects(cameraCorrection) #Apply the user-specified correction. This will fail if the image doesn't have binning metadata.
                except ValueError:
                    userSpecifiedBinning, pressedOk = QInputDialog.getInt(self.app.window, "Specify binning", "Please specify the camera binning that was used for these acquisitions.", 1, 1, 4)
                    if not pressedOk: #User pressed cancel
                        return
                    ref.correctCameraEffects(cameraCorrection, binning=userSpecifiedBinning)
            else:
                print("Using automatically detected camera corrections")
                ref.correctCameraEffects()
            if anSettings.extraReflectanceMetadata is not None: #if the ER is None, this means we are skipping the Extra reflection correction.
                if refMeta.systemName != anSettings.extraReflectanceMetadata.systemName:
                    ans = QMessageBox.question(self.app.window, "Uh Oh", f"The reference was acquired on system: {refMeta.systemName} while the extra reflectance correction was acquired on system: {anSettings.extraReflectanceMetadata.systemName}. Are you sure you want to continue?")
                    if ans == QMessageBox.No:
                        return
            print("Initializing analysis")
            if isinstance(anSettings, PWSRuntimeAnalysisSettings):
                analysis = PWSAnalysis(anSettings, ref)
            elif isinstance(anSettings, DynamicsRuntimeAnalysisSettings):
                analysis = DynamicsAnalysis(anSettings, ref)
            else:
                raise TypeError(f"Analysis settings of type: {type(anSettings)} are not supported.")
            useParallelProcessing = self.app.parallelProcessing
            #TODO would be good to estimate ram usage here and make a decision on whether or not to go parallel
            if (len(cellMetas) <= 3): #No reason to start 3 parallel processes for less than 3 cells.
                useParallelProcessing = False
            if useParallelProcessing:
                #Rather than copy arrays for each process, have read-only arrays that are shared between processes with shared memory. saves a few gigs of ram and speeds things up.
                print("AnalysisManager: Using parallel processing. Creating shared memory.")
                try:
                    analysis.copySharedDataToSharedMemory()
                except NotImplementedError:
                    pass
            else:
                print("Not using parallel processing.")
            #Run parallel/multithreaded processing
            t = self.AnalysisThread(cellMetas, analysis, anName, cameraCorrection, userSpecifiedBinning, useParallelProcessing)
            b = BusyDialog(self.app.window, "Processing. Please Wait...")
            t.finished.connect(b.accept)

            def handleError(e: Exception, trace: str):
                import traceback
                print(trace)
                QMessageBox.information(self.app.window, "Oh No", str(e))
            t.errorOccurred.connect(handleError)
            t.start()
            b.exec()
            warnings = t.warnings
            warnings = [(warn, md) for warn, md in warnings if md is not None]
            ret = (anName, anSettings.getSaveableSettings(), warnings)
            self.analysisDone.emit(*ret)
            return ret
        else:
            raise ValueError("Hmm. There appears to be a problem with different images using different `camera corrections`. Were all images taken on the same camera?")

    def _checkAutoCorrectionConsistency(self, cellMetas: List[AnalysisManagerMetaDataBase]) -> bool:
        """Confirm that all metadatas in cellMetas have identical camera corrections. otherwise we can't proceed"""
        camCorrections = [i.cameraCorrection for i in cellMetas]
        names = [os.path.split(i.filePath)[-1] for i in cellMetas]
        missing = []
        for name, cam in zip(names, camCorrections):
            if cam is None:
                missing.append(name)
        if len(missing) > 0:
            missingMessage = str(missing) if len(missing) <= 3 else 'Many cells are'
            QMessageBox.information(self.app.window, 'Hmm', f'{missingMessage} missing automatic camera correction')
            return False
        if len(set([hash(i) for i in camCorrections])) > 1:
            QMessageBox.information(self.app.window, 'Hmm', "Multiple camera corrections are present in the set of selected cells.")
            return False
        return True


    class AnalysisThread(QThread):
        errorOccurred = QtCore.pyqtSignal(Exception, str)

        def __init__(self, cellMetas, analysis, anName, cameraCorrection, userSpecifiedBinning, parallel):
            super().__init__()
            self.cellMetas = cellMetas
            self.analysis = analysis
            self.anName = anName
            self.cameraCorrection = cameraCorrection
            self.userSpecifiedBinning = userSpecifiedBinning
            self.warnings = None
            self.parallel = parallel

        def run(self):
            try:
                self.warnings = loadAndProcess(self.cellMetas, processorFunc=self._process, initArgs=[self.analysis, self.anName, self.cameraCorrection, self.userSpecifiedBinning],
                                     parallel=self.parallel, initializer=self._initializer) # Returns a list of Tuples, each tuple containing a list of warnings and the ICmetadata to go with it.
            except Exception as e:
                import traceback
                trace = traceback.format_exc()
                self.errorOccurred.emit(e, trace)


        @staticmethod
        def _initializer(analysis: AbstractAnalysis, analysisName: str, cameraCorrection: CameraCorrection, userSpecifiedBinning: Optional[int] = None):
            """This method is run once for each process that is spawned. it initialized _resources that are shared between each iteration of _process."""
            global pwspyAnalysisAppParallelGlobals
            print('initializing!')
            pwspyAnalysisAppParallelGlobals = {'analysis': analysis, 'analysisName': analysisName,
                                               'cameraCorrection': cameraCorrection, 'binning': userSpecifiedBinning}

        @staticmethod
        def _process(im: ICRawBase):
            """This method is run in parallel. once for each acquisition data that we want to analyze.
            Returns a list of AnalysisWarnings objects with the associated metadat object"""
            global pwspyAnalysisAppParallelGlobals
            analysis = pwspyAnalysisAppParallelGlobals['analysis']
            analysisName = pwspyAnalysisAppParallelGlobals['analysisName']
            cameraCorrection = pwspyAnalysisAppParallelGlobals['cameraCorrection']
            userSpecifiedBinning = pwspyAnalysisAppParallelGlobals['binning']
            if cameraCorrection is not None:
                if userSpecifiedBinning is None:
                    im.correctCameraEffects(cameraCorrection)
                else:
                    im.correctCameraEffects(cameraCorrection, binning=userSpecifiedBinning)
            else:
                im.correctCameraEffects()
            results, warnings = analysis.run(im)
            if len(warnings) > 0:
                md = im.metadata
            else:
                md = None
            im.metadata.saveAnalysis(results, analysisName)
            return warnings, md
