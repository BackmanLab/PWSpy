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

from PyQt5.QtWidgets import (QDockWidget, QWidget, QFrame, QVBoxLayout, QCheckBox, QScrollArea, QPushButton,
                             QGridLayout, QLineEdit, QLabel, QDialog, QTreeWidget, QTreeWidgetItem)
from PyQt5 import QtCore
from pwspy.analysis.compilation import DynamicsCompilerSettings, GenericCompilerSettings, PWSCompilerSettings, \
    PWSRoiCompilationResults
from pwspy.apps.PWSAnalysisApp.utilities.conglomeratedAnalysis import ConglomerateCompilerResults, ConglomerateCompilerSettings
from .widgets import ResultsTable, ResultsTableItem
import typing

from ..._taskManagers.compilationManager import CompilationManager
from ...componentInterfaces import ResultsTableController

if typing.TYPE_CHECKING:
    from pwspy.dataTypes import AcqDir, ICMetaData
    from pwspy.analysis.pws import PWSAnalysisSettings
    from pwspy.analysis.warnings import AnalysisWarning


class ResultsTableControllerDock(ResultsTableController, QDockWidget):
    def __init__(self, parent: QWidget):
        super().__init__("Results", parent=parent)
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.setObjectName('ResultsTableDock')
        self._widget = QWidget()
        self._widget.setLayout(QGridLayout())
        self._table = ResultsTable()
        checkBoxFrame = QFrame()
        checkBoxFrame.setLayout(QVBoxLayout())
        checkBoxFrame.layout().setContentsMargins(1, 1, 1, 1)
        checkBoxFrame.layout().setSpacing(1)
        self._checkBoxes = []
        for i, (name, (default, settingsName, compilerClass, tooltip)) in enumerate(self._table.columns.items()):
            c = QCheckBox(name)
            c.setCheckState(2) if default else c.setCheckState(0)
            c.stateChanged.connect(lambda state, j=i: self._table.setColumnHidden(j, state == 0))
            checkBoxFrame.layout().addWidget(c)
            self._checkBoxes.append(c)
        self._roiNameEdit = QLineEdit('.*', self._widget)
        self._roiNameEdit.setToolTip("ROIs matching this RegEx pattern will be compiled.")
        self._analysisNameEdit = QLineEdit('.*', self._widget)
        self._analysisNameEdit.setToolTip("Analyses matching this RegEx pattern will be compiled.")
        self._compileButton = QPushButton("Compile")

        self._compMan = CompilationManager(self.window())
        self._compileButton.released.connect(self._compMan.run)
        self._compMan.compilationDone.connect(self._handleCompilationResults)

        scroll = QScrollArea()
        scroll.setWidget(checkBoxFrame)
        scroll.verticalScrollBar().setStyleSheet("QScrollBar:horizontal { height: 10px; }")
        scroll.setMaximumWidth(checkBoxFrame.width() + 10)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.horizontalScrollBar().setEnabled(False)
        sidebar = QWidget()
        l = QGridLayout()
        l.addWidget(scroll, 0, 0, 1, 2)
        l.addWidget(QLabel('Analysis:'), 1, 0, 1, 1)
        l.addWidget(self._analysisNameEdit, 1, 1, 1, 1)
        l.addWidget(QLabel("Roi:"), 2, 0, 1, 1)
        l.addWidget(self._roiNameEdit, 2, 1, 1, 1)
        l.addWidget(self._compileButton, 3, 0, 1, 2)
        sidebar.setLayout(l)
        sidebar.setMaximumWidth(scroll.width()+10)
        self._widget.layout().addWidget(sidebar, 0, 0)
        self._widget.layout().addWidget(self._table, 0, 1)
        self.setWidget(self._widget)

    def addCompilationResult(self, result: ConglomerateCompilerResults, acquisition: AcqDir):
        self._table.addItem(ResultsTableItem(result, acquisition))

    def clearCompilationResults(self):
        self._table.clearCellItems()

    def getSettings(self) -> ConglomerateCompilerSettings:
        pwskwargs = {}
        dynkwargs = {}
        genkwargs = {}
        for checkBox in self._checkBoxes:
            defaultVisible, settingsName, compilerClass, tooltip = self._table.columns[checkBox.text()]
            if settingsName is not None:
                if compilerClass == PWSCompilerSettings:
                    pwskwargs[settingsName] = bool(checkBox.checkState())
                elif compilerClass == DynamicsCompilerSettings:
                    dynkwargs[settingsName] = bool(checkBox.checkState())
                elif compilerClass == GenericCompilerSettings:
                    genkwargs[settingsName] = bool(checkBox.checkState())
                else:
                    raise ValueError("All member of ResultsTable.columns that have a setting name defined must also have an associated compilerClass value")
        pws = PWSCompilerSettings(**pwskwargs)
        dyn = DynamicsCompilerSettings(**dynkwargs)
        gen = GenericCompilerSettings(**genkwargs)
        return ConglomerateCompilerSettings(pws, dyn, gen)

    def getRoiName(self) -> str:
        return self._roiNameEdit.text()

    def getAnalysisName(self) -> str:
        return self._analysisNameEdit.text()

    def _handleCompilationResults(self, inVal: typing.List[typing.Tuple[AcqDir, typing.List[typing.Tuple[ConglomerateCompilerResults, typing.Optional[typing.List[AnalysisWarning]]]]]]):
        #  Display warnings if necessary.
        warningStructure = []
        for acq, roiList in inVal:
            metaWarnings = []
            for result, warnList in roiList:
                if len(warnList) > 0:
                    metaWarnings.append((result, warnList))
            if len(metaWarnings) > 0:
                warningStructure.append((acq.pws, metaWarnings))
        if len(warningStructure) > 0:
            CompilationSummaryDisplay(self.window(), warningStructure)
        #  Display the results on the table
        results = [(acq, result) for acq, roiList in inVal for result, warnings in roiList]
        self.clearCompilationResults()
        [self.addCompilationResult(r, acq) for acq, r in results]


class CompilationSummaryDisplay(QDialog):
    def __init__(self, parent: typing.Optional[QWidget], warnings: typing.List[typing.Tuple[ICMetaData, typing.List[typing.Tuple[PWSRoiCompilationResults, typing.Optional[typing.List[AnalysisWarning]]]]]], analysisName: str = '', analysisSettings: PWSAnalysisSettings = None):
        super().__init__(parent=parent)
        self.setWindowTitle("Compilation Summary")
        layout = QVBoxLayout()
        self.warningTree = QTreeWidget(self)
        self.warningTree.setHeaderHidden(True)
        layout.addWidget(self.warningTree)
        self.setLayout(layout)
        self._addWarnings(warnings)
        self.show()

    def _addWarnings(self, warnings: typing.List[typing.Tuple[ICMetaData, typing.List[typing.Tuple[ConglomerateCompilerResults, typing.Optional[typing.List[AnalysisWarning]]]]]]):
        for meta, roiList in warnings:
            item = QTreeWidgetItem(self.warningTree)
            item.setText(0, meta.filePath)
            for roiResult, roiWarnList in roiList:
                if len(roiWarnList) > 0:
                    subItem = QTreeWidgetItem(item)
                    subItem.setText(0, f"{len(roiWarnList)} warnings: {roiResult.generic.roi.name} {roiResult.generic.roi.number}")
                    for warn in roiWarnList:
                        subItem2 = QTreeWidgetItem(subItem)
                        subItem2.setText(0, warn.shortMsg)
                        subItem2.setToolTip(0, warn.longMsg)

    def clearWarnings(self):
        self.warningTree.clear()