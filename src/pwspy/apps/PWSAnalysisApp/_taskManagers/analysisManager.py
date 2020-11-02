# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations

import logging
import os
from typing import Tuple, List, Optional
import typing
from PyQt5.QtCore import QThread

from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock import AbstractRuntimeAnalysisSettings
from pwspy.apps.PWSAnalysisApp.sharedWidgets import ScrollableMessageBox
from pwspy.apps.sharedWidgets.dialogs import BusyDialog
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox, QInputDialog
import pwspy.dataTypes as pwsdt
from pwspy.analysis import AbstractAnalysisSettings, AbstractAnalysis
from pwspy.analysis.dynamics import DynamicsAnalysis
from pwspy.analysis.pws import PWSAnalysis
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.runtimeSettings import PWSRuntimeAnalysisSettings, DynamicsRuntimeAnalysisSettings
from pwspy.analysis.warnings import AnalysisWarning
from pwspy.dataTypes import ICRawBase, ICMetaData, DynMetaData
from pwspy.utility.fileIO import loadAndProcess
if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.App import PWSApp


def safeCallback(func):
    """A decorator to make a function print its traceback without crashing."""
    def newFunc(*args):
        try:
            func(*args)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(e)
    return newFunc


class AnalysisManager(QtCore.QObject):
    analysisDone = QtCore.pyqtSignal(str, AbstractAnalysisSettings, list)

    def __init__(self, app: PWSApp):
        super().__init__()
        self.app = app

    def runList(self):
        """Run multiple queued analyses as specified by the user."""
        for anSettings in self.app.window.analysisSettings.getListedAnalyses():
            self.runSingle(anSettings)
            self.app.window.cellSelector.refreshCellItems()  # Refresh our displayed cell info

    @safeCallback
    def runSingle(self, anSettings: AbstractRuntimeAnalysisSettings) -> Tuple[str, AbstractAnalysisSettings, List[Tuple[List[AnalysisWarning], pwsdt.AcqDir]]]:
        """Run a single analysis batch"""
        logger = logging.getLogger(__name__)
        userSpecifiedBinning: Optional[int] = None
        cellMetas = anSettings.getCellMetadatas()
        refMeta = anSettings.getReferenceMetadata()
        cameraCorrection = anSettings.getSaveableSettings().cameraCorrection
        #Determine which cells already have an analysis by this name and raise a deletion dialog.
        conflictCells = []
        for cell in cellMetas:
            if anSettings.getAnalysisName() in cell.getAnalyses():
                conflictCells.append(cell)
        if len(conflictCells) > 0:
            ret = ScrollableMessageBox.question(self.app.window, "File Conflict", f"The following cells already have an analysis named {anSettings.getAnalysisName()}. Do you want to delete existing analyses and continue?: \n {', '.join([os.path.split(i.acquisitionDirectory.filePath)[-1] for i in conflictCells])}")
            if ret == QMessageBox.Yes:
                [cell.removeAnalysis(anSettings.getAnalysisName()) for cell in conflictCells]
            else:
                return
        if cameraCorrection is None:  # This means that the user has selected automatic cameraCorrection
            correctionsOk = self._checkAutoCorrectionConsistency(cellMetas + [refMeta])
        else:
            correctionsOk = True #We're using a user provided camera correction so we assume it's good to go.
        if correctionsOk:
            if isinstance(anSettings, PWSRuntimeAnalysisSettings):
                AnalysisClass = PWSAnalysis
                refMeta: ICMetaData
            elif isinstance(anSettings, DynamicsRuntimeAnalysisSettings):
                AnalysisClass = DynamicsAnalysis
                refMeta: DynMetaData
            else:
                raise TypeError(f"Analysis settings of type: {type(anSettings)} are not supported.")
            ref = refMeta.toDataClass()
            if cameraCorrection is not None:
                try:
                    ref.correctCameraEffects(cameraCorrection)  # Apply the user-specified correction. This will fail if the image doesn't have binning metadata.
                except ValueError:
                    userSpecifiedBinning, pressedOk = QInputDialog.getInt(self.app.window, "Specify binning", "Please specify the camera binning that was used for these acquisitions.", 1, 1, 4)
                    if not pressedOk:  # User pressed cancel
                        return
                    ref.correctCameraEffects(cameraCorrection, binning=userSpecifiedBinning)
            else:
                logger.info("Using automatically detected camera corrections")
                ref.correctCameraEffects()
            if anSettings.getExtraReflectanceMetadata() is not None:  # if the ER is None, this means we are skipping the Extra reflection correction.
                if refMeta.systemName != anSettings.getExtraReflectanceMetadata().systemName:
                    ans = QMessageBox.question(self.app.window, "Uh Oh", f"The reference was acquired on system: {refMeta.systemName} while the extra reflectance correction was acquired on system: {anSettings.extraReflectanceMetadata.systemName}. Are you sure you want to continue?")
                    if ans == QMessageBox.No:
                        return
            logger.info("Initializing analysis")
            analysis = AnalysisClass(anSettings.getSaveableSettings(), anSettings.getExtraReflectanceMetadata(), ref)
            useParallelProcessing = self.app.parallelProcessing
            if (len(cellMetas) <= 3): #No reason to start 3 parallel processes for less than 3 cells.
                useParallelProcessing = False
            if useParallelProcessing:
                #Rather than copy arrays for each process, have read-only arrays that are shared between processes with shared memory. saves a few gigs of ram and speeds things up.
                logger.info("AnalysisManager: Using parallel processing. Creating shared memory.")
                try:
                    analysis.copySharedDataToSharedMemory()
                except NotImplementedError:
                    pass
            else:
                logger.info("Not using parallel processing.")
            #Run parallel/multithreaded processing
            t = self.AnalysisThread(cellMetas, analysis, anSettings.getAnalysisName(), cameraCorrection, userSpecifiedBinning, useParallelProcessing)
            b = BusyDialog(self.app.window, "Processing. Please Wait...")
            t.finished.connect(b.accept)

            def handleError(e: Exception, trace: str):
                logger.warning(trace)
                QMessageBox.information(self.app.window, "Oh No", str(e))
            t.errorOccurred.connect(handleError)
            t.start()
            b.exec()
            warnings = t.warnings
            warnings = [(warn, md) for warn, md in warnings if md is not None]
            ret = (anSettings.getAnalysisName(), anSettings.getSaveableSettings(), warnings)
            self.analysisDone.emit(*ret)
            return ret
        else:
            raise ValueError("Hmm. There appears to be a problem with different images using different `camera corrections`. Were all images taken on the same camera?")

    def _checkAutoCorrectionConsistency(self, cellMetas: List[pwsdt.AnalysisManagerMetaDataBase]) -> bool:
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
        def _initializer(analysis: AbstractAnalysis, analysisName: str, cameraCorrection: pwsdt.CameraCorrection, userSpecifiedBinning: Optional[int] = None):
            """This method is run once for each process that is spawned. it initialized _resources that are shared between each iteration of _process."""
            global pwspyAnalysisAppParallelGlobals
            logger = logging.getLogger(__name__)
            logger.info('Initializing analysis shared data.')
            pwspyAnalysisAppParallelGlobals = {'analysis': analysis, 'analysisName': analysisName,
                                               'cameraCorrection': cameraCorrection, 'binning': userSpecifiedBinning}

        @staticmethod
        def _process(im: pwsdt.ICRawBase):
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

