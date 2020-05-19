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
import traceback

from IPython.core.magics import logging
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QMessageBox, QMainWindow
from PyQt5 import QtCore
from pwspy.apps.sharedWidgets.dialogs import BusyDialog
from pwspy.apps.PWSAnalysisApp._taskManagers.analysisManager import safeCallback
import re
from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateCompiler, ConglomerateAnalysisResults
import typing
if typing.TYPE_CHECKING:
    from typing import Tuple, List, Optional
    from pwspy.dataTypes import AcqDir
    from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateCompilerSettings, ConglomerateCompilerResults
    from pwspy.analysis.warnings import AnalysisWarning


class CompilationManager(QtCore.QObject):
    compilationDone = QtCore.pyqtSignal(list)

    def __init__(self, window: QMainWindow):
        super().__init__()
        self.window = window

    @safeCallback
    def run(self) -> List[Tuple[AcqDir, List[Tuple[ConglomerateCompilerResults, Optional[List[AnalysisWarning]]]]]]:
        roiName: str = self.window.resultsTable.getRoiName()
        analysisName: str = self.window.resultsTable.getAnalysisName()
        settings: ConglomerateCompilerSettings = self.window.resultsTable.getSettings()
        cellMetas: List[AcqDir] = self.window.cellSelector.getSelectedCellMetas()
        if len(cellMetas) == 0:
            QMessageBox.information(self.window, "What?", "Please select at least one cell.")
            return None
        compiler = ConglomerateCompiler(settings)
        b = BusyDialog(self.window, "Processing. Please Wait...")
        t = self.CompilationThread(cellMetas, compiler, roiName, analysisName)
        t.finished.connect(b.accept)
        t.errorOccurred.connect(lambda e: QMessageBox.information(self.window, 'Uh Oh', str(e)))
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

        def __init__(self, cellMetas: List[AcqDir], compiler: ConglomerateCompiler, roiNamePattern: str, analysisNamePattern: str):
            super().__init__()
            self.cellMetas = cellMetas
            self.roiNamePattern = roiNamePattern
            self.analysisNamePattern = analysisNamePattern
            self.compiler = compiler
            self.result = None

        def run(self):
            try:
                self.result = []
                for acq in self.cellMetas:
                    self.result.append(self._process(acq, self.compiler, self.roiNamePattern, self.analysisNamePattern)) # A list of Tuples. each tuple containing a list of warnings and the Acquisition to go with it.
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning("Compilation error:")
                logger.exception(e)
                self.errorOccurred.emit(e)

        @staticmethod
        def _process(acq: AcqDir, compiler: ConglomerateCompiler, roiNamePattern: str, analysisNamePattern: str) -> Tuple[AcqDir, List[Tuple[ConglomerateCompilerResults, List[AnalysisWarning]]]]:
            rois = [acq.loadRoi(name, num, fformat) for name, num, fformat in acq.getRois() if re.match(roiNamePattern, name)]
            pwsAnalysisResults = [acq.pws.loadAnalysis(name) for name in acq.pws.getAnalyses() if re.match(analysisNamePattern, name)] if acq.pws is not None else []
            dynamicAnalysisResults = [acq.dynamics.loadAnalysis(name) for name in acq.dynamics.getAnalyses() if re.match(analysisNamePattern, name)] if acq.dynamics is not None else []
            conglomeratedAnalysisResults = []
            for pws in pwsAnalysisResults:  # Find the analyses with matching names and pair them.
                for dyn in dynamicAnalysisResults:
                    if pws.analysisName == dyn.analysisName:
                        conglomeratedAnalysisResults.append(ConglomerateAnalysisResults(pws, dyn))
                        pwsAnalysisResults.remove(pws) #Once an analysis has been paired remove it from the list of analyses
                        dynamicAnalysisResults.remove(dyn)
            conglomeratedAnalysisResults += [ConglomerateAnalysisResults(pws, None) for pws in pwsAnalysisResults] #Any remaining analyses couldn't be paired. Just add them on their own.
            conglomeratedAnalysisResults += [ConglomerateAnalysisResults(None, dyn) for dyn in dynamicAnalysisResults]
            ret = []
            for analysisResult in conglomeratedAnalysisResults:
                for roi in rois:
                    cResults, warnings = compiler.run(analysisResult, roi)
                    ret.append((cResults, warnings))
            return acq, ret
