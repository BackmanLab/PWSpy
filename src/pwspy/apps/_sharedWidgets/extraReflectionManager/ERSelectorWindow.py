from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QMessageBox, QWidget, QCheckBox, QVBoxLayout, \
    QPushButton, QLineEdit, QComboBox, QGridLayout, QLabel, QDialogButtonBox, QHBoxLayout, QAbstractItemView, QMenu, \
    QAction

from pwspy import moduleConsts
from pwspy.apps.PWSAnalysisApp._sharedWidgets.tables import DatetimeTableWidgetItem
from pwspy.dataTypes import ExtraReflectanceCube
from pwspy.dataTypes._ExtraReflectanceCubeClass import ERMetadata
import numpy as np
from .exceptions import OfflineError

import typing

from pwspy.utility import PlotNd

if typing.TYPE_CHECKING:
    from pwspy.apps._sharedWidgets.extraReflectionManager import ERManager
    from pwspy.apps._sharedWidgets.extraReflectionManager.ERIndex import ERIndexCube


class ERTableWidgetItem:
    def __init__(self, fileName: str, description: str, idTag: str, name: str, downloaded: bool):
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.systemName = self.idTag.split('_')[1]
        self.datetime = datetime.strptime(self.idTag.split('_')[2], moduleConsts.dateTimeFormat)
        self.name = name

        self.sysItem = QTableWidgetItem(self.systemName)
        self.dateItem = DatetimeTableWidgetItem(self.datetime)
        self._checkBox = QCheckBox()
        self.checkBoxWidget = QWidget()
        l = QHBoxLayout()
        l.setAlignment(QtCore.Qt.AlignCenter)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self._checkBox)
        self.checkBoxWidget.setLayout(l)
        self.sysItem.setToolTip('\n'.join([f'File Name: {self.fileName}', f'ID: {self.idTag}', f'Description: {self.description}']))
        if downloaded:
            #Item can be selected. Checkbox no longer usable
            self._checkBox.setCheckState(QtCore.Qt.Checked)
            self._checkBox.setEnabled(False)
            self.sysItem.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
        else:
            #Checkbox can be checked to allow downloading. Nothing else can be done.
            self.sysItem.setFlags(QtCore.Qt.NoItemFlags)
            self.dateItem.setFlags(QtCore.Qt.NoItemFlags)
        self._downloaded = downloaded

    @property
    def downloaded(self): return self._downloaded

    def isChecked(self):
        return self._checkBox.isChecked()


class ERSelectorWindow(QDialog):
    selectionChanged = QtCore.pyqtSignal(ERMetadata)
    def __init__(self, manager: ERManager, parent: Optional[QWidget] = None):
        self._manager = manager
        self._selectedId: str = None
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle("Extra Reflectance Selector")
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(self)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.showContextMenu)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setRowCount(0)
        self.table.setColumnCount(3)
        self.table.setSortingEnabled(True)
        self.table.setHorizontalHeaderLabels([" ", "System", "Date"])
        self.table.setColumnWidth(0, 10)

        self.downloadButton = QPushButton("Download Checked Items")
        self.downloadButton.released.connect(self._downloadCheckedItems)
        # self.updateButton = QPushButton('Update Index')
        # self.updateButton.setToolTip("Update the index containing information about which Extra Reflectance Cubes are available for download.")
        # self.updateButton.released.connect(self._updateIndex)
        self.acceptSelectionButton = QPushButton("Accept Selection")
        self.acceptSelectionButton.released.connect(self.accept)
        self.layout().addWidget(self.table)
        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.downloadButton)
        # l.addWidget(self.updateButton)
        w = QWidget()
        w.setLayout(l)
        self.layout().addWidget(w)
        self.layout().addWidget(self.acceptSelectionButton)
        try:
            self._manager.download('index.json', parentWidget=self)
        except OfflineError:
            msbBox = QMessageBox.information(self, 'Offline Mode', 'Could not update `Extra Reflectance` index file. Connection to Google Drive failed.')
        self._initialize()

    # def _updateIndex(self):
    #     self._manager.download("index.json", parentWidget=self)
    #     self._initialize()

    def _initialize(self):
        self._manager.rescan()
        self._items: List[ERTableWidgetItem] = []
        for item in self._manager.dataComparator.local.index.cubes:
            self._addItem(item)

    def _addItem(self, item: ERIndexCube):
        status = self._manager.dataComparator.local.status
        tableItem = ERTableWidgetItem(fileName=item.fileName, description=item.description, idTag=item.idTag, name=item.name,
                                      downloaded=status[status['idTag'] == item.idTag].iloc[0]['Local Status'] == self._manager.dataComparator.local.DataStatus.found.value)
        self._items.append(tableItem)
        self.table.setRowCount(len(self._items))
        self.table.setCellWidget(self.table.rowCount() - 1, 0, tableItem.checkBoxWidget)
        self.table.setItem(self.table.rowCount() - 1, 1, tableItem.sysItem)
        self.table.setItem(tableItem.sysItem.row(), 2, tableItem.dateItem)

    def showContextMenu(self, pos: QPoint):
        index = self.table.indexAt(pos)
        widgetItem: ERTableWidgetItem = [i for i in self._items if i.sysItem.row() == index.row()][0]
        menu = QMenu()
        displayAction = QAction("Display Info")
        displayAction.triggered.connect(lambda: self.displayInfo(widgetItem))
        menu.addAction(displayAction)
        if widgetItem.downloaded:
            plotAction = QAction("Plot Data")
            plotAction.triggered.connect(lambda: PlotNd(ExtraReflectanceCube.fromHdfFile(self._manager._directory, widgetItem.name).data))
            menu.addAction(plotAction)
        menu.exec(self.mapToGlobal(pos))

    def displayInfo(self, item: ERTableWidgetItem):
        message = QMessageBox.information(self, item.name, '\n\n'.join([f'FileName: {item.fileName}',
                                                                      f'ID Tag: {item.idTag}',
                                                                      f'Description: {item.description}']))

    def _downloadCheckedItems(self):
        for item in self._items:
            if item.isChecked() and not item.downloaded:
                # If the checkbox is enabled then it hasn't been downloaded yet. if it is checked then it should be downloaded
                self._manager.download(item.fileName, parentWidget=self)
        self._initialize()

    def accept(self) -> None:
        try:
            rowIndex = [i.row() for i in self.table.selectedIndexes()[::self.table.columnCount()]][0] #  There should be only one.
            self.setSelection(self._items[rowIndex].idTag)
        except IndexError: # Nothing was selected
            pass
        super().accept()

    def getSelectedId(self):
        return self._selectedId

    def setSelection(self, idTag: str):
        md = self._manager.getMetadataFromId(idTag)
        self._selectedId = idTag
        self.selectionChanged.emit(md)

