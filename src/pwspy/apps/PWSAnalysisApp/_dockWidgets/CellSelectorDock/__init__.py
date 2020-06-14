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
import logging
import os
import re
from typing import List, Optional

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QGridLayout, QSplitter, \
    QSizePolicy, QMessageBox
import pwspy.dataTypes as pwsdt
from pwspy.apps.PWSAnalysisApp._dockWidgets.CellSelectorDock.widgets import ReferencesTableItem
from .widgets import CellTableWidgetItem, CellTableWidget, ReferencesTable
from ...componentInterfaces import CellSelector


class CellSelectorDock(CellSelector, QDockWidget):
    """This dockwidget is used by the user to select which cells they want to act upon (run an analysis, plot, etc.)"""
    selectionChanged = QtCore.pyqtSignal(list)

    def __init__(self):
        super().__init__("Cell Selector")
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.setObjectName('CellSelectorDock')  # needed for restore state to work
        self._widget = QWidget(self)
        layout = QVBoxLayout()
        self.tableWidget = CellTableWidget(self._widget)
        self._selectionChangeDebounce = QtCore.QTimer()  # This timer prevents the selectionChanged signal from firing too rapidly.
        self._selectionChangeDebounce.setInterval(500)
        self._selectionChangeDebounce.setSingleShot(True)
        self._selectionChangeDebounce.timeout.connect(lambda: self.selectionChanged.emit(self.getSelectedCellMetas()))

        self.tableWidget.itemSelectionChanged.connect(self._selectionChangeDebounce.start)
        self.refTableWidget = ReferencesTable(self._widget, self.tableWidget)
        self._filterWidget = QWidget(self._widget)
        self.pathFilter = QComboBox(self._filterWidget)
        self.pathFilter.setEditable(True)
        self.pathFilter.setStyleSheet('''*     
        QComboBox QAbstractItemView 
            {
            min-width: 200px;
            }
        ''')  # This makes the dropdown wider so we can actually read.
        width = self.pathFilter.minimumSizeHint().width()
        self.pathFilter.view().setMinimumWidth(width)
        self.expressionFilter = QLineEdit(self._filterWidget)
        description = "Python boolean expression.\n\tCell#: {num},\n\tAnalysis names: {analyses},\n\tROI names: {rois},\n\tID tag: {idTag}.\nE.G. `{num} > 5 and 'nucleus' in {rois}`"
        self.expressionFilter.setPlaceholderText(description.replace('\n', '').replace('\t', ''))  #Strip out the white space
        self.expressionFilter.setToolTip(description)
        self.expressionFilter.returnPressed.connect(self._executeFilter)
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
        _.setStretchFactor(1, 0); _.setStretchFactor(0, 1)  # Make the references column so it doesn't resize on stretching.
        layout.addWidget(_)
        layout.addWidget(self._filterWidget)
        self._widget.setLayout(layout)
        self.setWidget(self._widget)

    def addCell(self, fileName: str, workingDir: str):
        try:
            cell = pwsdt.AcqDir(fileName)
        except OSError:
            return
        cellItem = CellTableWidgetItem(cell, os.path.split(fileName)[0][len(workingDir) + 1:],
                                        int(fileName.split('Cell')[-1]))
        if cellItem.isReference():
            self.refTableWidget.updateReferences(True, [cellItem])
        self.tableWidget.addCellItem(cellItem)

    def addCells(self, fileNames: List[str], workingDir: str):
        cellItems = []
        for f in fileNames:
            try:
                acq = pwsdt.AcqDir(f)
            except OSError as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load {f}")
                logger.exception(e)
                continue
            cellItems.append(CellTableWidgetItem(acq, os.path.split(f)[0][len(workingDir) + 1:],
                                        int(f.split('Cell')[-1])))
        refItems = [i for i in cellItems if i.isReference()]
        if len(refItems)>0:
            self.refTableWidget.updateReferences(True, refItems)
        self.tableWidget.addCellItems(cellItems)

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
        self.pathFilter.currentIndexChanged.connect(self._executeFilter)  # reconnect

    def _executeFilter(self): #TODO the filter should also hide the reference items. this will require some changes ot the referece item table code.
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
                    analyses = []
                    if item.acqDir.pws:
                        analyses += item.acqDir.pws.getAnalyses()
                    if item.acqDir.dynamics:
                        analyses += item.acqDir.dynamics.getAnalyses()
                    ret = bool(eval(expr.format(num=item.num, analyses=analyses, rois=[i[0] for i in item.acqDir.getRois()], idTag=item.acqDir.idTag)))
                except Exception as e:
                    QMessageBox.information(self, 'Hmm', f'{expr} is not a valid boolean expression.')
                    return
            else:
                ret = True
            if match and ret:
                self.tableWidget.setRowHidden(item.row, False)
            else:
                self.tableWidget.setRowHidden(item.row, True)

    def getSelectedCellMetas(self) -> List[pwsdt.AcqDir]:
        return [i.acqDir for i in self.tableWidget.selectedCellItems]

    def getAllCellMetas(self) -> List[pwsdt.AcqDir]:
        return [i.acqDir for i in self.tableWidget.cellItems]

    def getSelectedReferenceMeta(self) -> Optional[pwsdt.AcqDir]:
        return self.refTableWidget.selectedReferenceMeta

    def setSelectedCells(self, cells: List[pwsdt.AcqDir]):
        idTags = [i.idTag for i in cells]
        for item in self.tableWidget.cellItems:
            if item.acqDir.idTag in idTags:
                item.setSelected(True)
            else:
                item.setSelected(False)

    def setSelectedReference(self, ref: pwsdt.AcqDir):
        idTag = ref.idTag
        for i in range(self.refTableWidget.rowCount()):
            refitem: ReferencesTableItem = self.refTableWidget.item(i, 0)
            if refitem.item.acqDir.idTag == idTag:
                refitem.setSelected(True)
            else:
                refitem.setSelected(False)

    def setHighlightedCells(self, cells: List[pwsdt.AcqDir]):
        idTags = [i.idTag for i in cells]
        for item in self.tableWidget.cellItems:
            if item.acqDir.idTag in idTags:
                item.setHighlighted(True)
            else:
                item.setHighlighted(False)

    def setHighlightedReference(self, ref: pwsdt.AcqDir):
        idTag = ref.idTag
        for i in range(self.refTableWidget.rowCount()):
            refitem: ReferencesTableItem = self.refTableWidget.item(i, 0)
            if refitem.item.acqDir.idTag == idTag:
                refitem.setHighlighted(True)
            else:
                refitem.setHighlighted(False)

    def refreshCellItems(self):
        self.tableWidget.refreshCellItems()
