from __future__ import annotations
from typing import Tuple, List, Optional
import typing

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QMessageBox

if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.App import PWSApp
    from pwspy.dataTypes import ImCube

from PyQt5 import QtCore

from pwspy.analysis.compilation import RoiCompiler, RoiCompilationResults, CompilerSettings
from pwspy.analysis.warnings import AnalysisWarning


from pwspy.apps.sharedWidgets.dialogs import BusyDialog
from pwspy.apps.PWSAnalysisApp._taskManagers.analysisManager import safeCallback
from pwspy.utility.io import loadAndProcess
import re


class CompilationManager(QtCore.QObject):
    compilationDone = QtCore.pyqtSignal(list)

    def __init__(self, app: PWSApp):
        super().__init__()
        self.app = app

    @safeCallback
    def run(self) -> List[Tuple[ImCube.ICMetaData, List[Tuple[RoiCompilationResults, Optional[List[AnalysisWarning]]]]]]:
        roiName: str = self.app.window.resultsTable.getRoiName()
        analysisName: str = self.app.window.resultsTable.getAnalysisName()
        settings: CompilerSettings = self.app.window.resultsTable.getSettings()
        cellMetas: List[ImCube.ICMetaData] = self.app.window.cellSelector.getSelectedCellMetas()
        if len(cellMetas) == 0:
            QMessageBox.information(self.app.window, "What?", "Please select at least one cell.")
            return None
        compiler = RoiCompiler(settings)
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

        def __init__(self, cellMetas: List[ImCube.ICMetaData], compiler: RoiCompiler, roiNamePattern: str, analysisNamePattern: str):
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
                                             metadataOnly=True)  # A list of Tuples. each tuple containing a list of warnings and the ImCube.ICMetaData to go with it.
            except Exception as e:
                self.errorOccurred.emit(e)

        @staticmethod
        def _process(md: ImCube.ICMetaData, compiler: RoiCompiler, roiNamePattern: str, analysisNamePattern: str) -> Tuple[ImCube.ICMetaData, List[Tuple[RoiCompilationResults, List[AnalysisWarning]]]]:
            rois = [md.loadRoi(name, num, fformat) for name, num, fformat in md.getRois() if re.match(roiNamePattern, name)]
            analysisResults = [md.loadAnalysis(name) for name in md.getAnalyses() if re.match(analysisNamePattern, name)]
            ret = []
            for analysisResult in analysisResults:
                for roi in rois:
                    cResults, warnings = compiler.run(analysisResult, roi)
                    ret.append((cResults, warnings))
            return md, ret