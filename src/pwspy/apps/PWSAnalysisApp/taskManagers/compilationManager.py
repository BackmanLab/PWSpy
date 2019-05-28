from __future__ import annotations
from typing import Tuple, List, Optional
import typing
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
        self.compilationDone.emit(results)
        return results