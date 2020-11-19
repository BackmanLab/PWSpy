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
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QGridLayout, QSplitter, \
    QSizePolicy, QMessageBox, QPushButton, QMenu, QAction
import pwspy.dataTypes as pwsdt
from pwspy.apps.PWSAnalysisApp._dockWidgets.CellSelectorDock.widgets import ReferencesTableItem
from .widgets import CellTableWidgetItem, CellTableWidget, ReferencesTable
from pwspy.apps.PWSAnalysisApp.componentInterfaces import CellSelector
from pwspy.apps.PWSAnalysisApp.pluginInterfaces import CellSelectorPluginSupport


class CellSelectorDock(CellSelector, QDockWidget):
    """This dockwidget is used by the user to select which cells they want to act upon (run an analysis, plot, etc.)"""
    def __init__(self, parent: QWidget):
        super().__init__("Cell Selector", parent=parent)
        self._pluginSupport = CellSelectorPluginSupport(self, self)
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.setObjectName('CellSelectorDock')  # needed for restore state to work
        self._widget = QWidget(self)
        layout = QVBoxLayout()
        addedColumns = []
        for plugin in self._pluginSupport.getPlugins():
            addedColumns += plugin.additionalColumnNames()
        self._tableWidget = CellTableWidget(self._widget, addedColumns)
        self._selectionChangeDebounce = QtCore.QTimer()  # This timer prevents the selectionChanged signal from firing too rapidly.
        self._selectionChangeDebounce.setInterval(500)
        self._selectionChangeDebounce.setSingleShot(True)
        self._selectionChangeDebounce.timeout.connect(lambda: self._pluginSupport.notifyCellSelectionChanged(self.getSelectedCellMetas()))
        self._tableWidget.itemSelectionChanged.connect(self._selectionChangeDebounce.start)

        self._refTableWidget = ReferencesTable(self._widget, self._tableWidget)
        self._refSelectionChangeDebounce = QtCore.QTimer()
        self._refSelectionChangeDebounce.setInterval(500)
        self._refSelectionChangeDebounce.setSingleShot(True)
        self._refSelectionChangeDebounce.timeout.connect(lambda: self._pluginSupport.notifyReferenceSelectionChanged(self.getSelectedReferenceMeta()))
        self._refTableWidget.itemSelectionChanged.connect(self._refSelectionChangeDebounce.start)

        self._bottomBar = QWidget(self._widget)

        self._pathFilter = QComboBox(self._bottomBar)
        self._pathFilter.setEditable(True)
        self._pathFilter.setStyleSheet('''*     
        QComboBox QAbstractItemView 
            {
            min-width: 200px;
            }
        ''')  # This makes the dropdown wider so we can actually read.
        width = self._pathFilter.minimumSizeHint().width()
        self._pathFilter.view().setMinimumWidth(width)

        self._expressionFilter = QLineEdit(self._bottomBar)
        description = "Python boolean expression.\n\tCell#: {num},\n\tAnalysis names: {analyses},\n\tROI names: {rois},\n\tID tag: {idTag}.\nE.G. `{num} > 5 and 'nucleus' in {rois}`"
        self._expressionFilter.setPlaceholderText(description.replace('\n', '').replace('\t', ''))  #Strip out the white space
        self._expressionFilter.setToolTip(description)
        self._expressionFilter.returnPressed.connect(self._executeFilter)

        self._pluginsButton = QPushButton("Tools", self)
        self._pluginsButton.released.connect(self._showPluginMenu)

        _ = QGridLayout()
        _.addWidget(self._pathFilter, 0, 0, 1, 1)
        _.addWidget(self._expressionFilter, 0, 1, 1, 1)
        _.addWidget(self._pluginsButton, 0, 2, 1, 1)
        self._bottomBar.setLayout(_)
        _ = QSplitter()
        _.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        _.addWidget(self._tableWidget)
        _.addWidget(self._refTableWidget)
        _.setCollapsible(0, False)
        _.setCollapsible(1, False)
        _.setSizes([300, 100])
        _.setStretchFactor(1, 0); _.setStretchFactor(0, 1)  # Make the references column so it doesn't resize on stretching.
        layout.addWidget(_)
        layout.addWidget(self._bottomBar)
        self._widget.setLayout(layout)
        self.setWidget(self._widget)

    def _showPluginMenu(self):
        menu = QMenu("plugin menu", self)
        for plugin in self._pluginSupport.getPlugins():
            action = QAction(plugin.getName())
            action.triggered.connect(lambda checked, p=plugin: p.onPluginSelected())
            menu.addAction(action)
        menu.exec(self._pluginsButton.mapToGlobal(QPoint(0, self._pluginsButton.height())))

    # def _addCell(self, fileName: str, workingDir: str):
    #     try:
    #         cell = pwsdt.AcqDir(fileName)
    #     except OSError:
    #         return
    #     cellItem = CellTableWidgetItem(cell, os.path.split(fileName)[0][len(workingDir) + 1:],
    #                                     int(fileName.split('Cell')[-1]))
    #     if cellItem.isReference():
    #         self._refTableWidget.updateReferences(True, [cellItem])
    #     self._tableWidget.addCellItem(cellItem)

    def _addCells(self, acquisitions: List[pwsdt.AcqDir], workingDir: str):
        cellItems = []
        for acq in acquisitions:
            addedWidgets = []
            for plugin in self._pluginSupport.getPlugins():
                addedWidgets += plugin.getTableWidgets(acq)
            cellItems.append(CellTableWidgetItem(acq, os.path.split(acq.filePath)[0][len(workingDir) + 1:],
                                        int(acq.filePath.split('Cell')[-1]),  additionalWidgets=addedWidgets))
        refItems = [i for i in cellItems if i.isReference()]
        if len(refItems) > 0:
            self._refTableWidget.updateReferences(True, refItems)
        self._tableWidget.addCellItems(cellItems)

    def _clearCells(self):  #This is used publically, probably shouldn't be.
        self._cells = []
        self._tableWidget.clearCellItems()

    def _updateFilters(self):
        try:
            self._pathFilter.currentIndexChanged.disconnect()
        except:
            pass
        self._pathFilter.clear()
        self._pathFilter.addItem('.*')
        paths = []
        for i in self._tableWidget.cellItems:
            paths.append(i.path)
        self._pathFilter.addItems(set(paths))
        self._pathFilter.currentIndexChanged.connect(self._executeFilter)  # reconnect

    def _executeFilter(self): #TODO the filter should also hide the reference items. this will require some changes ot the referece item table code.
        path = self._pathFilter.currentText()
        path = path.replace('\\', '\\\\')
        for item in self._tableWidget.cellItems:
            text = item.path.replace(r'\\', r'\\\\')
            try:
                match = re.match(path, text)
            except re.error:
                QMessageBox.information(self, 'Hmm', f'{path} is not a valid regex expression.')
                return
            expr = self._expressionFilter.text()
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
                self._tableWidget.setRowHidden(item.row, False)
            else:
                self._tableWidget.setRowHidden(item.row, True)

    def close(self):
        """This makes sure the application metadata is saved."""
        self._clearCells()

    def loadNewCells(self, fileNames: List[str], workingDir: str):
        self._clearCells()
        acqs = []
        for f in fileNames:
            try:
                acqs.append(pwsdt.AcqDir(f))
            except OSError as e:
                logger = logging.getLogger(__name__)
                logger.warning(f"Failed to load {f}")
                logger.exception(e)
                continue
        self._pluginSupport.notifyNewCellsLoaded(acqs)
        self._addCells(acqs, workingDir)
        self._updateFilters()


    def getSelectedCellMetas(self) -> List[pwsdt.AcqDir]:
        return [i.acqDir for i in self._tableWidget.selectedCellItems]

    def getAllCellMetas(self) -> List[pwsdt.AcqDir]:
        return [i.acqDir for i in self._tableWidget.cellItems]

    def getSelectedReferenceMeta(self) -> Optional[pwsdt.AcqDir]:
        return self._refTableWidget.selectedReferenceMeta

    def setSelectedCells(self, cells: List[pwsdt.AcqDir]):
        idTags = [i.idTag for i in cells]
        for item in self._tableWidget.cellItems:
            if item.acqDir.idTag in idTags:
                item.setSelected(True)
            else:
                item.setSelected(False)

    def setSelectedReference(self, ref: pwsdt.AcqDir):
        idTag = ref.idTag
        for i in range(self._refTableWidget.rowCount()):
            refitem: ReferencesTableItem = self._refTableWidget.item(i, 0)
            if refitem.item.acqDir.idTag == idTag:
                refitem.setSelected(True)
            else:
                refitem.setSelected(False)

    def setHighlightedCells(self, cells: List[pwsdt.AcqDir]):
        idTags = [i.idTag for i in cells]
        for item in self._tableWidget.cellItems:
            if item.acqDir.idTag in idTags:
                item.setHighlighted(True)
            else:
                item.setHighlighted(False)

    def setHighlightedReference(self, ref: pwsdt.AcqDir):
        idTag = ref.idTag
        for i in range(self._refTableWidget.rowCount()):
            refitem: ReferencesTableItem = self._refTableWidget.item(i, 0)
            if refitem.item.acqDir.idTag == idTag:
                refitem.setHighlighted(True)
            else:
                refitem.setHighlighted(False)

    def refreshCellItems(self):
        self._tableWidget.refreshCellItems()
