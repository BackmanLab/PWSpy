from __future__ import annotations
from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QTableWidgetItem, QFrame, QVBoxLayout, QCheckBox, \
    QScrollArea, QPushButton, QLayout, QGridLayout, QAction, QLineEdit, QLabel, QSizePolicy
from PyQt5 import QtCore
from pwspy.analysis.compilation import RoiCompilationResults, CompilerSettings
from .widgets import ResultsTable, ResultsTableItem
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ICMetaData


class ResultsTableDock(QDockWidget):
    # noinspection PyTypeChecker
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
        for i, (name, (default, settingsName, tooltip)) in enumerate(self.table.columns.items()):
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
        l.addWidget(QLabel('PWSAnalysis:'), 1, 0, 1, 1)
        l.addWidget(self.analysisNameEdit, 1, 1, 1, 1)
        l.addWidget(QLabel("Roi:"), 2, 0, 1, 1)
        l.addWidget(self.roiNameEdit, 2, 1, 1, 1)
        l.addWidget(self.compileButton, 3, 0, 1, 2)
        sidebar.setLayout(l)
        sidebar.setMaximumWidth(scroll.width()+10)
        self._widget.layout().addWidget(sidebar, 0, 0)
        self._widget.layout().addWidget(self.table, 0, 1)
        self.setWidget(self._widget)

    def addCompilationResult(self, result: RoiCompilationResults, metadata: ICMetaData):
        self.table.addItem(ResultsTableItem(result, metadata))

    def clearCompilationResults(self):
        self.table.clearCellItems()

    def getSettings(self):
        kwargs = {}
        for checkBox in self.checkBoxes:
            defaultVisible, settingsName, tooltip = self.table.columns[checkBox.text()]
            if settingsName is not None:
                kwargs[settingsName] = bool(checkBox.checkState())
        return CompilerSettings(**kwargs)

    def getRoiName(self) -> str:
        return self.roiNameEdit.text()

    def getAnalysisName(self) -> str:
        return self.analysisNameEdit.text()
