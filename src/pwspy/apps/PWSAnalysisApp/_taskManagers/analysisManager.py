from __future__ import annotations
import os
import traceback
from typing import Tuple, List
import typing

from PyQt5.QtCore import QThread

from pwspy.apps.PWSAnalysisApp._sharedWidgets.dialogs import BusyDialog
from pwspy.utility.misc import profileDec

if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.App import  PWSApp
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from pwspy.dataTypes import ImCube, CameraCorrection, ExtraReflectanceCube
from pwspy.analysis import AnalysisSettings
from pwspy.analysis._analysisClass import Analysis
from pwspy.analysis.warnings import AnalysisWarning
from pwspy.dataTypes._ICMetaDataClass import ICMetaData
from pwspy.utility.io import loadAndProcess
import threading
from multiprocessing.util import Finalize
from multiprocessing.sharedctypes import RawArray
import numpy as np


def safeCallback(func):
    """A decorator to make a function print its traceback without crashing."""
    def newFunc(*args):
        try:
            func(*args)
        except:
            traceback.print_exc()
    return newFunc

class AnalysisManager(QtCore.QObject):
    analysisDone = QtCore.pyqtSignal(str, AnalysisSettings, list)

    def __init__(self, app: PWSApp):
        super().__init__()
        self.app = app

    def runList(self):
        """Run multiple queued analyses as specified by the user."""
        for anName, anSettings, cellMetas, refMeta, camCorrection in self.app.window.analysisSettings.getListedAnalyses():
            self.runSingle(anName, anSettings, cellMetas, refMeta, camCorrection)
            [cellItem.refresh() for cellMeta in cellMetas for cellItem in self.app.window.cellSelector.tableWidget.cellItems if cellMeta == cellItem.cube]

    @safeCallback
    def runSingle(self, anName: str, anSettings: AnalysisSettings, cellMetas: List[ICMetaData], refMeta: ICMetaData,
                  cameraCorrection: CameraCorrection) -> Tuple[str, AnalysisSettings, List[Tuple[List[AnalysisWarning], ICMetaData]]]:
        """Run a single analysis batch"""
        #Determine which cells already have an analysis by this name and raise a deletion dialog.
        conflictCells = []
        for cell in cellMetas:
            if anName in cell.getAnalyses():
                conflictCells.append(cell)
        if len(conflictCells) > 0:
            ret = QMessageBox.question(self.app.window, "File Conflict", f"The following cells already have an analysis named {anName}. Do you want to delete existing analyses and continue?: \n {', '.join([os.path.split(i.filePath)[-1] for i in conflictCells])}")
            if ret == QMessageBox.Yes:
                [cell.removeAnalysis(anName) for cell in conflictCells]
            else:
                return
        if cameraCorrection is None: # This means that the user has selected automatic cameraCorrection
            correctionsOk = self._checkAutoCorrectionConsistency(cellMetas + [refMeta])
        else:
            correctionsOk = True #We're using a user provided camera correction so we assume it's good to go.
        if correctionsOk:
            ref = ImCube.fromMetadata(refMeta)
            if cameraCorrection is not None:
                ref.correctCameraEffects(cameraCorrection) #Apply the user-specified correction
            else:
                print("Using automatically detected camera corrections")
                ref.correctCameraEffects()
            if anSettings.extraReflectanceId is None: #the id is None, this means we are skipping the Extra reflection correction.
                erCube = None
            else:
                erMeta = self.app.ERManager.getMetadataFromId(anSettings.extraReflectanceId)
                erCube = ExtraReflectanceCube.fromMetadata(erMeta)
            analysis = Analysis(anSettings, ref, erCube)
            #replace read-only arrays that are shared between processes with shared memory. saves a few gigs of ram and speeds things up.
            refdata = RawArray('f', analysis.ref.data.size)
            refdata = np.frombuffer(refdata, dtype=np.float32).reshape(analysis.ref.data.shape)
            np.copyto(refdata, analysis.ref.data)
            analysis.ref.data = refdata
            iedata = RawArray('f', analysis.extraReflection.data.size)
            iedata = np.frombuffer(iedata, dtype=np.float32).reshape(analysis.extraReflection.data.shape)
            np.copyto(iedata, analysis.extraReflection.data)
            analysis.extraReflection.data = iedata
            #Run parallel processing
            t = self.AnalysisThread(cellMetas, analysis, anName, cameraCorrection, self.app.parallelProcessing)
            b = BusyDialog(self.app.window, "Processing. Please Wait...")
            t.finished.connect(b.accept)
            t.errorOccurred.connect(lambda e: QMessageBox.information(self.app.window, 'Uh Oh', str(e)))
            t.start()
            b.exec()
            warnings = t.warnings
            warnings = [(warn, md) for warn, md in warnings if md is not None]
            ret = (anName, anSettings, warnings)
            self.analysisDone.emit(*ret)
            return ret

    def _checkAutoCorrectionConsistency(self, cellMetas: List[ICMetaData]) -> bool:
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
        errorOccurred = QtCore.pyqtSignal(Exception)

        def __init__(self, cellMetas, analysis, anName, cameraCorrection, parallel):
            super().__init__()
            self.cellMetas = cellMetas
            self.analysis = analysis
            self.anName = anName
            self.cameraCorrection = cameraCorrection
            self.warnings = None
            self.parallel = parallel

        def run(self):
            try:
                self.warnings = loadAndProcess(self.cellMetas, processorFunc=self._process, initArgs=[self.analysis, self.anName, self.cameraCorrection],
                                     parallel=self.parallel, initializer=self._initializer) # A list of Tuples. each tuple containing a list of warnings and the ICmetadata to go with it.
            except Exception as e:
                self.errorOccurred.emit(e)


        @staticmethod
        def _initializer(analysis: Analysis, analysisName: str, cameraCorrection: CameraCorrection):
            """This method is run once for each process that is spawned. it initialized _resources that are shared between each iteration of _process."""
            global pwspyAnalysisAppParallelGlobals
            global saveThreadResource
            saveThreadResource = AnalysisManager.AnalysisThread.ThreadResource().__enter__()
            Finalize(saveThreadResource, saveThreadResource.__exit__, exitpriority=16)
            print('initializing!')
            pwspyAnalysisAppParallelGlobals = {'analysis': analysis, 'analysisName': analysisName,
                                               'cameraCorrection': cameraCorrection}

        @staticmethod
        def _process(im: ImCube):
            """This method is run in parallel. once for each dataTypes that we want to analyze."""
            global pwspyAnalysisAppParallelGlobals
            global saveThreadResource
            if saveThreadResource.thread:
                saveThreadResource.thread.start()
            analysis = pwspyAnalysisAppParallelGlobals['analysis']
            analysisName = pwspyAnalysisAppParallelGlobals['analysisName']
            cameraCorrection = pwspyAnalysisAppParallelGlobals['cameraCorrection']
            if cameraCorrection is not None:
                im.correctCameraEffects(cameraCorrection)
            else:
                im.correctCameraEffects()
            results, warnings = analysis.run(im)
            if len(warnings) > 0:
                md = im.metadata
            else:
                md = None
            if saveThreadResource.thread:
                saveThreadResource.thread.join()
            saveThreadResource.thread = threading.Thread(target=lambda: im.metadata.saveAnalysis(results, analysisName))
            return warnings, md

        class ThreadResource:
            """This hacky thing is used in _initializer and _process, it allows us to save to harddisk in a separate thread
            and make sure that the process doesn't quit before the last file is saved. This is needed since Pool doesn't allow
            a deinitializer method"""

            def __init__(self):
                self.thread = None

            def __enter__(self):
                return self

            def __exit__(self):
                if self.thread:
                    self.thread.start()
                    self.thread.join()