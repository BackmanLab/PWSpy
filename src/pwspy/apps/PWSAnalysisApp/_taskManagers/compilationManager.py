from __future__ import annotations
from typing import Tuple, List, Optional
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtCore
from pwspy.analysis.compilation import PWSRoiCompiler, PWSRoiCompilationResults, PWSCompilerSettings
from pwspy.analysis.warnings import AnalysisWarning
from pwspy.apps.sharedWidgets.dialogs import BusyDialog
from pwspy.apps.PWSAnalysisApp._taskManagers.analysisManager import safeCallback
from pwspy.utility.fileIO import loadAndProcess
import re
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.App import PWSApp
    from pwspy.dataTypes import AcqDir, ICMetaData


# TODO make this work for dynamics and generic compiler classes

class CompilationManager(QtCore.QObject):
    compilationDone = QtCore.pyqtSignal(list)

    def __init__(self, app: PWSApp):
        super().__init__()
        self.app = app

    @safeCallback
    def run(self) -> List[Tuple[ICMetaData, List[Tuple[PWSRoiCompilationResults, Optional[List[AnalysisWarning]]]]]]:
        roiName: str = self.app.window.resultsTable.getRoiName()
        analysisName: str = self.app.window.resultsTable.getAnalysisName()
        settings: PWSCompilerSettings = self.app.window.resultsTable.getSettings()
        cellMetas: List[AcqDir] = self.app.window.cellSelector.getSelectedCellMetas()
        cellMetas: List[ICMetaData] = [i.pws for i in cellMetas]  # Just use the pws data
        if len(cellMetas) == 0:
            QMessageBox.information(self.app.window, "What?", "Please select at least one cell.")
            return None
        compiler = PWSRoiCompiler(settings)
        b = BusyDialog(self.app.window, "Processing. Please Wait...")
        t = self.CompilationThread(cellMetas, compiler, roiName, analysisName)
        t.finished.connect(b.accept)
        t.errorOccurred.connect(lambda e: QMessageBox.information(self.app.window, 'Uh Oh', str(e)))
        t.start()
        b.exec()
        results = t.result
        if results is not None: #If None then an error must have occurred
            self.compilationDone.emit(results)
            return results
        else:
            return None

    class CompilationThread(QThread):
        errorOccurred = QtCore.pyqtSignal(Exception)

        def __init__(self, cellMetas: List[ICMetaData], compiler: PWSRoiCompiler, roiNamePattern: str, analysisNamePattern: str):
            super().__init__()
            self.cellMetas = cellMetas
            self.roiNamePattern = roiNamePattern
            self.analysisNamePattern = analysisNamePattern
            self.compiler = compiler
            self.result = None

        def run(self):
            try:
                self.result = loadAndProcess(self.cellMetas, processorFunc=self._process, procArgs=[self.compiler, self.roiNamePattern, self.analysisNamePattern],
                                             parallel=False,
                                             metadataOnly=True)  # A list of Tuples. each tuple containing a list of warnings and the ICMetaData to go with it.
            except Exception as e:
                self.errorOccurred.emit(e)

        @staticmethod
        def _process(md: ICMetaData, compiler: PWSRoiCompiler, roiNamePattern: str, analysisNamePattern: str) -> Tuple[ICMetaData, List[Tuple[PWSRoiCompilationResults, List[AnalysisWarning]]]]:
            rois = [md.acquisitionDirectory.loadRoi(name, num, fformat) for name, num, fformat in md.acquisitionDirectory.getRois() if re.match(roiNamePattern, name)]
            analysisResults = [md.loadAnalysis(name) for name in md.getAnalyses() if re.match(analysisNamePattern, name)]
            ret = []
            for analysisResult in analysisResults:
                for roi in rois:
                    cResults, warnings = compiler.run(analysisResult, roi)
                    ret.append((cResults, warnings))
            return md, ret