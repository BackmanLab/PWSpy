import os
import re
from typing import List, Dict

from PyQt5.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QGridLayout, QSplitter, \
    QSizePolicy, QMessageBox

from pwspy.apps.PWSAnalysisApp.dockWidgets.CellSelectorDock.widgets import ReferencesTableItem
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
        self.pathFilter.setStyleSheet('''*     
        QComboBox QAbstractItemView 
            {
            min-width: 200px;
            }
        ''') #This makes the dropdown wider so we can actually read.
        width = self.pathFilter.minimumSizeHint().width()
        self.pathFilter.view().setMinimumWidth(width)
        self.expressionFilter = QLineEdit(self._filterWidget)
        self.expressionFilter.setPlaceholderText("Python boolean expression. Cell#: {num}, Analysis names: {analyses}, ROI names: {rois}")
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
        _.setStretchFactor(1, 0); _.setStretchFactor(0, 1) # Make the references column so it doesn't resize on stretching.
        layout.addWidget(_)
        layout.addWidget(self._filterWidget)
        self._widget.setLayout(layout)
        self.setWidget(self._widget)

    def addCell(self, fileName: str, workingDir: str):
        try:
            cell = ICMetaData.loadAny(fileName)
        except OSError as e: # Could not find a valid file
            print(e)
            return
        cellItem = CellTableWidgetItem(cell, os.path.split(fileName)[0][len(workingDir) + 1:],
                                   int(fileName.split('Cell')[-1]))
        if cellItem.isReference():
            self.refTableWidget.updateReferences(True, [cellItem])
        self.tableWidget.addCellItem(cellItem)

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
        for item in self.tableWidget.cellItems:
            text = item.path.replace(r'\\', r'\\\\')
            try:
                match = re.match(path, text)
            except re.error:
                QMessageBox.information(self, 'Hmm', f'{path} is not a valid regex expression.')
                return
            expr = self.expressionFilter.text()
            if expr.strip() != '':
                try:
                    ret = bool(eval(expr.format(num=item.num, analyses=item.cube.getAnalyses(), rois=[i[0] for i in item.cube.getRois()])))
                except Exception:
                    QMessageBox.information(self, 'Hmm', f'{expr} is not a valid boolean expression.')
                    return
            else:
                ret = True
            if match and ret:
                self.tableWidget.setRowHidden(item.row, False)
            else:
                self.tableWidget.setRowHidden(item.row, True)

    def getSelectedCellMetas(self):
        return [i.cube for i in self.tableWidget.selectedCellItems]

    def getSelectedReferenceMeta(self):
        return self.refTableWidget.selectedReferenceMeta

    def setSelectedCells(self, cells: List[ICMetaData]):
        idTags = [i.idTag for i in cells]
        for item in self.tableWidget.cellItems:
            if item.cube.idTag in idTags:
                item.setSelected(True)
            else:
                item.setSelected(False)

    def setSelectedReference(self, ref: ICMetaData):
        idTag = ref.idTag
        for i in range(self.refTableWidget.rowCount()):
            refitem: ReferencesTableItem = self.refTableWidget.item(i, 0)
            if refitem.item.cube.idTag == idTag:
                refitem.setSelected(True)
            else:
                refitem.setSelected(False)
