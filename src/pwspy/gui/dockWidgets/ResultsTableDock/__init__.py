from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QTableWidgetItem, QFrame, QVBoxLayout, QCheckBox, \
    QScrollArea, QPushButton, QLayout, QGridLayout
from PyQt5 import QtCore

from .widgets import ResultsTable


class ResultsTableDock(QDockWidget):
    def __init__(self):
        super().__init__("Results")
        self.setObjectName('ResultsTableDock')
        self._widget = QWidget()
        self._widget.setLayout(QGridLayout())
        self.table = ResultsTable()
        self.checkBoxes = QFrame()
        self.checkBoxes.setLayout(QVBoxLayout())
        self.checkBoxes.layout().setContentsMargins(1, 1, 1, 1)
        self.checkBoxes.layout().setSpacing(1)
        for i, n in enumerate(self.table.columns):
            c = QCheckBox(n)
            c.setCheckState(2)
            f = lambda state, i=i: self.table.setColumnHidden(i, state == 0)
            c.stateChanged.connect(f)
            self.checkBoxes.layout().addWidget(c)

        scroll = QScrollArea()
        scroll.setWidget(self.checkBoxes)
        scroll.verticalScrollBar().setStyleSheet("QScrollBar:horizontal { height: 10px; }")
        scroll.setMaximumWidth(self.checkBoxes.width() + 10)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll.horizontalScrollBar().setEnabled(False)
        sidebar = QVBoxLayout()
        sidebar.addWidget(scroll)
        self.compileButton = QPushButton("Compile")
        sidebar.addWidget(self.compileButton)
        # sidebar.setSizeConstraint(QLayout.SetMinimumSize)
        self._widget.layout().addLayout(sidebar, 0, 0)
        self._widget.layout().addWidget(self.table, 0, 1)
        self.setWidget(self._widget)
