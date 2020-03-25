from __future__ import annotations
from PyQt5.QtWidgets import QDockWidget, QWidget, QFrame, QVBoxLayout, QCheckBox, \
    QScrollArea, QPushButton, QGridLayout, QLineEdit, QLabel
from PyQt5 import QtCore

from pwspy.analysis.compilation.dynamics import DynamicsCompilerSettings
from pwspy.analysis.compilation.generic import GenericCompilerSettings
from pwspy.analysis.compilation.pws import PWSCompilerSettings
from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateCompilerResults, ConglomerateCompilerSettings
from .widgets import ResultsTable, ResultsTableItem
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes._metadata import AcqDir


class ResultsTableDock(QDockWidget): #TODO update this for the new conglomoerate classes.
    def __init__(self):
        super().__init__("Results")
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.setObjectName('ResultsTableDock')
        self._widget = QWidget()
        self._widget.setLayout(QGridLayout())
        self.table = ResultsTable()
        checkBoxFrame = QFrame()
        checkBoxFrame.setLayout(QVBoxLayout())
        checkBoxFrame.layout().setContentsMargins(1, 1, 1, 1)
        checkBoxFrame.layout().setSpacing(1)
        self.checkBoxes = []
        for i, (name, (default, settingsName, compilerClass, tooltip)) in enumerate(self.table.columns.items()):
            c = QCheckBox(name)
            c.setCheckState(2) if default else c.setCheckState(0)
            c.stateChanged.connect(lambda state, j=i: self.table.setColumnHidden(j, state == 0))
            checkBoxFrame.layout().addWidget(c)
            self.checkBoxes.append(c)
        self.roiNameEdit = QLineEdit('.*', self._widget)
        self.roiNameEdit.setToolTip("ROIs matching this RegEx pattern will be compiled.")
        self.analysisNameEdit = QLineEdit('.*', self._widget)
        self.analysisNameEdit.setToolTip("Analyses matching this RegEx pattern will be compiled.")
        self.compileButton = QPushButton("Compile")

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
        l.addWidget(self.analysisNameEdit, 1, 1, 1, 1)
        l.addWidget(QLabel("Roi:"), 2, 0, 1, 1)
        l.addWidget(self.roiNameEdit, 2, 1, 1, 1)
        l.addWidget(self.compileButton, 3, 0, 1, 2)
        sidebar.setLayout(l)
        sidebar.setMaximumWidth(scroll.width()+10)
        self._widget.layout().addWidget(sidebar, 0, 0)
        self._widget.layout().addWidget(self.table, 0, 1)
        self.setWidget(self._widget)

    def addCompilationResult(self, result: ConglomerateCompilerResults, acquisition: AcqDir):
        self.table.addItem(ResultsTableItem(result, acquisition))

    def clearCompilationResults(self):
        self.table.clearCellItems()

    def getSettings(self) -> ConglomerateCompilerSettings:
        pwskwargs = {}
        dynkwargs = {}
        genkwargs = {}
        for checkBox in self.checkBoxes:
            defaultVisible, settingsName, compilerClass, tooltip = self.table.columns[checkBox.text()]
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
        return self.roiNameEdit.text()

    def getAnalysisName(self) -> str:
        return self.analysisNameEdit.text()
