from __future__ import annotations
from datetime import datetime
from typing import List, Optional

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QMessageBox, QWidget, QCheckBox, QVBoxLayout, \
    QPushButton, QLineEdit, QComboBox, QGridLayout, QLabel, QDialogButtonBox, QHBoxLayout, QAbstractItemView, QMenu, \
    QAction, QTreeWidget, QTreeWidgetItem

from pwspy import moduleConsts
from pwspy.apps.PWSAnalysisApp._sharedWidgets.tables import DatetimeTableWidgetItem
from pwspy.dataTypes import ExtraReflectanceCube
from pwspy.dataTypes._ExtraReflectanceCubeClass import ERMetadata
import numpy as np
from .exceptions import OfflineError

import typing

from pwspy.utility import PlotNd

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
    from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndexCube


class ERTreeWidgetItem(QTreeWidgetItem):
    def __init__(self, fileName: str, description: str, idTag: str, name: str, downloaded: bool):
        super().__init__()
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.systemName = self.idTag.split('_')[1]
        self.datetime = datetime.strptime(self.idTag.split('_')[2], moduleConsts.dateTimeFormat)
        self.name = name

        self.setText(0, datetime.strftime(self.datetime, '%B %d, %Y'))
        self.setToolTip(0, '\n'.join([f'File Name: {self.fileName}', f'ID: {self.idTag}', f'Description: {self.description}']))

        if downloaded:
            #Item can be selected. Checkbox no longer usable
            self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
            self.setCheckState(0, QtCore.Qt.PartiallyChecked)
        else:
            #Checkbox can be checked to allow downloading. Nothing else can be done.
            self.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            self.setCheckState(0, QtCore.Qt.Unchecked)
        self._downloaded = downloaded

    @property
    def downloaded(self): return self._downloaded

    def __lt__(self, other: ERTreeWidgetItem):  # Needed for sorting by date
        return self.datetime < other.datetime

    def isChecked(self) -> bool:
        return self.checkState(0) == QtCore.Qt.Checked



class ERSelectorWindow(QDialog):
    selectionChanged = QtCore.pyqtSignal(object) #Usually an ERMetadata object, sometimes None
    def __init__(self, manager: ERManager, parent: Optional[QWidget] = None):
        self._manager = manager
        self._selectedId: str = None
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle("Extra Reflectance Selector")
        self.setLayout(QVBoxLayout())
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.showContextMenu)
        self.downloadButton = QPushButton("Download Checked Items")
        self.downloadButton.released.connect(self._downloadCheckedItems)
        self.acceptSelectionButton = QPushButton("Accept Selection")
        self.acceptSelectionButton.released.connect(self.accept)
        self.layout().addWidget(self.tree)
        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.downloadButton)
        w = QWidget()
        w.setLayout(l)
        self.layout().addWidget(w)
        self.layout().addWidget(self.acceptSelectionButton)
        try:
            self._manager.download('index.json', parentWidget=self)
        except OfflineError:
            msgBox = QMessageBox.information(self, 'Offline Mode', 'Could not update `Extra Reflectance` index file. Connection to Google Drive failed.')
        self._initialize()


    def _initialize(self):
        self._items: List[ERTreeWidgetItem] = []
        self.tree.clear()
        self._manager.dataComparator.local.rescan()
        for item in self._manager.dataComparator.local.index.cubes:
            self._addItem(item)
        #Sort items by date
        for item in [self.tree.invisibleRootItem().child(i) for i in range(self.tree.invisibleRootItem().childCount())]:
            item.sortChildren(0, QtCore.Qt.AscendingOrder)
        ig = QTreeWidgetItem()
        ig.setText(0, "Ignore")
        self.tree.invisibleRootItem().addChild(ig)

    def _addItem(self, item: ERIndexCube):
        status = self._manager.dataComparator.local.status
        treeItem = ERTreeWidgetItem(fileName=item.fileName, description=item.description, idTag=item.idTag, name=item.name,
                                      downloaded=status[status['idTag'] == item.idTag].iloc[0]['Local Status'] == self._manager.dataComparator.local.DataStatus.found.value)
        self._items.append(treeItem)
        _ = self.tree.invisibleRootItem()
        if treeItem.systemName not in [_.child(i).text(0) for i in range(_.childCount())]:
            sysNameItem = QTreeWidgetItem(_, [treeItem.systemName])
            sysNameItem.setFlags(QtCore.Qt.ItemIsEnabled)  # Don't allow selecting
            _.addChild(sysNameItem)
        parent = [i for i in [_.child(i) for i in range(_.childCount())] if i.text(0) == treeItem.systemName][0]
        parent.addChild(treeItem)

    def showContextMenu(self, pos: QPoint):
        widgetItem: ERTreeWidgetItem = self.tree.itemAt(pos)
        if not isinstance(widgetItem, ERTreeWidgetItem):
            return  # Some treeItems exist which are not our custom ERTreeWidgetItem. Not menu for these items.
        menu = QMenu()
        displayAction = QAction("Display Info")
        displayAction.triggered.connect(lambda: self.displayInfo(widgetItem))
        menu.addAction(displayAction)
        if widgetItem.downloaded:
            plotAction = QAction("Plot Data")
            plotAction.triggered.connect(lambda: PlotNd(ExtraReflectanceCube.fromHdfFile(self._manager._directory, widgetItem.name).data))
            menu.addAction(plotAction)
        menu.exec(self.mapToGlobal(pos))

    def displayInfo(self, item: ERTreeWidgetItem):
        message = QMessageBox.information(self, item.name, '\n\n'.join([f'FileName: {item.fileName}',
                                                                      f'ID Tag: {item.idTag}',
                                                                      f'Description: {item.description}']))

    def _downloadCheckedItems(self):
        for item in self._items:
            if item.isChecked() and not item.downloaded:
                # If it is checked then it should be downloaded
                self._manager.download(item.fileName, parentWidget=self)
        self._initialize()

    def accept(self) -> None:
        if self.tree.selectedItems()[0].text(0) == 'Ignore':
            self.setSelection(None)
            super().accept()
        else:
            try:
                self.setSelection(self.tree.selectedItems()[0].idTag)
                super().accept()
            except IndexError:  # Nothing was selected
                msg = QMessageBox.information(self, 'Uh oh!', 'No item was selected!')

    def getSelectedId(self):
        return self._selectedId

    def setSelection(self, idTag: str):
        if idTag is None:
            md = None
        else:
            md = self._manager.getMetadataFromId(idTag)
        self._selectedId = idTag
        self.selectionChanged.emit(md)

