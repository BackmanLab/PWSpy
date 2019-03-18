import os
import re

from PyQt5.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QGridLayout, QSplitter, \
    QSizePolicy, QMessageBox

from .widgets import CellTableWidgetItem, CellTableWidget, ReferencesTable
from pwspy.imCube.ICMetaDataClass import ICMetaData


class CellSelectorDock(QDockWidget):
    def __init__(self):
        super().__init__("Cell Selector")
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.setObjectName('CellSelectorDock')  # needed for restore state to work
        self._widget = QWidget(self)
        layout = QVBoxLayout()
        self.tableWidget = CellTableWidget(self._widget)
        self.refTableWidget = ReferencesTable(self._widget, self.tableWidget)
        self._filterWidget = QWidget(self._widget)
        self.pathFilter = QComboBox(self._filterWidget)
        self.pathFilter.setEditable(True)
        width = self.pathFilter.minimumSizeHint().width()
        self.pathFilter.view().setMinimumWidth(width)
        self.expressionFilter = QLineEdit(self._filterWidget)
        self.expressionFilter.setPlaceholderText("Python boolean expression. Cell#: {num}")
        self.expressionFilter.returnPressed.connect(self.executeFilter)
        _ = QGridLayout()
        _.addWidget(self.pathFilter, 0, 0, 1, 1)
        _.addWidget(self.expressionFilter, 0, 1, 1, 1)
        self._filterWidget.setLayout(_)
        _ = QSplitter()
        _.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        _.addWidget(self.tableWidget)
        _.addWidget(self.refTableWidget)
        _.setCollapsible(0, False)
        _.setCollapsible(1, False)
        _.setSizes([300, 100])
        layout.addWidget(_)
        layout.addWidget(self._filterWidget)
        self._widget.setLayout(layout)
        self.setWidget(self._widget)
        self._cells = []

    def addCell(self, fileName: str, workingDir: str):
        self._cells.append(ICMetaData.loadAny(fileName))
        cell = CellTableWidgetItem(self._cells[-1], os.path.split(fileName)[0][len(workingDir) + 1:],
                                   int(fileName.split('Cell')[-1]))
        self.tableWidget.addCellItem(cell)

    def clearCells(self):
        self._cells = []
        self.tableWidget.clearCellItems()

    def updateFilters(self):
        try:
            self.pathFilter.currentIndexChanged.disconnect()
        except:
            pass
        self.pathFilter.clear()
        self.pathFilter.addItem('.*')
        paths = []
        for i in self.tableWidget.cellItems:
            paths.append(i.path)
        self.pathFilter.addItems(set(paths))
        self.pathFilter.currentIndexChanged.connect(self.executeFilter)  # reconnect

    def executeFilter(self):
        path = self.pathFilter.currentText()
        path = path.replace('\\', '\\\\')
        for i in range(self.tableWidget.rowCount()):
            text = self.tableWidget.item(i, 0).text()
            text = text.replace(r'\\', r'\\\\')
            try:
                match = re.match(path, text)
            except re.error:
                QMessageBox.information(self, 'Hmm', f'{text} is not a valid regex expression.')
                return
            expr = self.expressionFilter.text()
            if expr.strip() != '':
                try:
                    ret = bool(eval(expr.format(num=self.tableWidget.item(i, 1).number)))
                except Exception:
                    QMessageBox.information(self, 'Hmm', f'{expr} is not a valid boolean expression.')
                    return
            else:
                ret = True
            if match and ret:
                self.tableWidget.setRowHidden(i, False)
            else:
                self.tableWidget.setRowHidden(i, True)

    def getSelectedCellMetas(self):
        return [i.cube for i in self.tableWidget.selectedCellItems]

    def getSelectedReferenceMeta(self):
        return self.refTableWidget.selectedReferenceMeta