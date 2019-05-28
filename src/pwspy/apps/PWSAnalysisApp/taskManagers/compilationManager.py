from __future__ import annotations
from typing import Tuple, List, Optional
import typing

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QMessageBox

if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.App import PWSApp

from PyQt5 import QtCore

from pwspy.analysis.compilation import RoiCompiler, RoiCompilationResults, CompilerSettings
from pwspy.analysis.warnings import AnalysisWarning


from pwspy.apps.PWSAnalysisApp.sharedWidgets.dialogs import BusyDialog
from pwspy.apps.PWSAnalysisApp.taskManagers.analysisManager import safeCallback
from pwspy.imCube import ICMetaData
from pwspy.utility.io import loadAndProcess


class CompilationManager(QtCore.QObject):
    compilationDone = QtCore.pyqtSignal(list)

    def __init__(self, app: PWSApp):
        super().__init__()
        self.app = app

    @safeCallback
    def run(self) -> List[Tuple[ICMetaData, List[Tuple[RoiCompilationResults, Optional[List[AnalysisWarning]]]]]]:
        roiName: str = self.app.window.resultsTable.getRoiName()
        analysisName: str = self.app.window.resultsTable.getAnalysisName()
        settings: CompilerSettings = self.app.window.resultsTable.getSettings()
        cellMetas: List[ICMetaData] = self.app.window.cellSelector.getSelectedCellMetas()
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

        def __init__(self, cellMetas: List[ICMetaData], compiler: RoiCompiler, roiName: str, analysisName: str):
            super().__init__()
            self.cellMetas = cellMetas
            self.roiName = roiName
            self.analysisName = analysisName
            self.compiler = compiler
            self.result = None

        def run(self):
            try:
                self.result = loadAndProcess(self.cellMetas, processorFunc=self._process, procArgs=[self.compiler, self.roiName, self.analysisName],
                           parallel=False,
                           metadataOnly=True)  # A list of Tuples. each tuple containing a list of warnings and the ICmetadata to go with it.
            except Exception as e:
                self.errorOccurred.emit(e)

        @staticmethod
        def _process(md: ICMetaData, compiler: RoiCompiler, roiName: str, analysisName: str) -> Tuple[ICMetaData, List[Tuple[RoiCompilationResults, List[AnalysisWarning]]]]:
            rois = [md.loadRoi(name, num, fformat) for name, num, fformat in md.getRois() if name == roiName]
            analysisResults = md.loadAnalysis(analysisName)
            ret = []
            for roi in rois:
                cResults, warnings = compiler.run(analysisResults, roi)
                ret.append((cResults, warnings))
            return md, ret