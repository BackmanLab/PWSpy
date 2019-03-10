from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QTableWidgetItem, QFrame, QVBoxLayout, QCheckBox

from .widgets import ResultsTable


class ResultsTableDock(QDockWidget):
    def __init__(self):
        super().__init__("Results")
        self.setObjectName('ResultsTableDock')
        columns = ('Cell#', "RMS", 'Reflectance', 'ld', 'etc.')
        self._widget = QWidget()
        self._widget.setLayout(QHBoxLayout())
        self.table = ResultsTable()
        self.table.setRowCount(5)
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.verticalHeader().hide()
        self.table.setItem(1, 1, QTableWidgetItem("rms"))
        self.checkBoxes = QFrame()
        self.checkBoxes.setLayout(QVBoxLayout())
        for i, n in enumerate(columns):
            c = QCheckBox(n)
            c.setCheckState(2)
            f = lambda state, i=i: self.table.setColumnHidden(i, state == 0)
            c.stateChanged.connect(f)
            self.checkBoxes.layout().addWidget(c)
        self._widget.layout().addWidget(self.checkBoxes)
        self._widget.layout().addWidget(self.table)
        self.setWidget(self._widget)