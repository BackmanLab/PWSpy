from __future__ import annotations
import os
import traceback
from typing import Tuple, List, Optional
import typing
if typing.TYPE_CHECKING:
    from .App import  PWSApp
    import multiprocessing as mp
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from pwspy.imCube import ImCube, CameraCorrection, ExtraReflectanceCube
from pwspy.analysis import AnalysisSettings
from pwspy.analysis.analysisClass import Analysis
from pwspy.analysis.warnings import AnalysisWarning
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility.io import loadAndProcess
from pwspy.analysis.compilation import CompilerSettings, RoiCompiler, RoiCompilationResults
import threading
from multiprocessing.util import Finalize
import multiprocessing
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
            [self.app.window.cellSelector.cellItems[cellMeta.idTag].refresh() for cellMeta in cellMetas]

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
                ref.correctCameraEffects(auto=True)
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
            warnings = loadAndProcess(cellMetas, processorFunc=self._process, initArgs=[analysis, anName, cameraCorrection],
                                      parallel=self.app.parallelProcessing, initializer=self._initializer) # A list of Tuples. each tuple containing a list of warnings and the ICmetadata to go with it.
            warnings = [(warn, md) for warn, md in warnings if md is not None]
            ret = (anName, anSettings, warnings)
            self.analysisDone.emit(*ret)
            return ret

    @staticmethod
    def _process(im: ImCube):
        """This method is run in parallel. once for each imCube that we want to analyze."""
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
            im.correctCameraEffects(auto=True)
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
            self.thread.start()
            self.thread.join()

    @staticmethod
    def _initializer(analysis: Analysis, analysisName: str, cameraCorrection: CameraCorrection):
        """This method is run once for each process that is spawned. it initialized resources that are shared between each iteration of _process."""
        global pwspyAnalysisAppParallelGlobals
        global saveThreadResource
        saveThreadResource = AnalysisManager.ThreadResource().__enter__()
        Finalize(saveThreadResource, saveThreadResource.__exit__, exitpriority=16)
        print('initializing!')
        pwspyAnalysisAppParallelGlobals = {'analysis': analysis, 'analysisName':  analysisName, 'cameraCorrection': cameraCorrection}

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


class CompilationManager(QtCore.QObject):
    compilationDone = QtCore.pyqtSignal(list)

    def __init__(self, app: PWSApp):
        super().__init__()
        self.app = app

    @staticmethod
    def _process(md: ICMetaData, compiler: RoiCompiler, roiName: str, analysisName: str) -> Tuple[ICMetaData, List[Tuple[RoiCompilationResults, List[AnalysisWarning]]]]:
        rois = [md.loadRoi(name, num, fformat) for name, num, fformat in md.getRois() if name == roiName]
        analysisResults = md.loadAnalysis(analysisName)
        ret = []
        for roi in rois:
            cResults, warnings = compiler.run(analysisResults, roi)
            ret.append((cResults, warnings))
        return md, ret

    @safeCallback
    def run(self) -> List[Tuple[ICMetaData, List[Tuple[RoiCompilationResults, Optional[List[AnalysisWarning]]]]]]:
        roiName: str = self.app.window.resultsTable.getRoiName()
        analysisName: str = self.app.window.resultsTable.getAnalysisName()
        settings: CompilerSettings = self.app.window.resultsTable.getSettings()
        cellMetas: List[ICMetaData] = self.app.window.cellSelector.getSelectedCellMetas()
        compiler = RoiCompiler(settings)

        results: List[Tuple[ICMetaData, List[Tuple[RoiCompilationResults, List[AnalysisWarning]]]]] = loadAndProcess(cellMetas, processorFunc=self._process, procArgs=[compiler, roiName, analysisName],
                                  parallel=False, metadataOnly=True) # A list of Tuples. each tuple containing a list of warnings and the ICmetadata to go with it.
        # newresults = []
        # for i in results:
        #     newresults.extend(i)# Convert from list of lists to just a long list
        self.compilationDone.emit(results)
        return results
