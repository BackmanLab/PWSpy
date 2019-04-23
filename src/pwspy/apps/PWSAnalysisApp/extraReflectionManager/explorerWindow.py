from typing import List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QMessageBox, QWidget, QCheckBox, QVBoxLayout, \
    QPushButton, QLineEdit, QComboBox, QGridLayout, QLabel, QDialogButtonBox, QHBoxLayout

from .manager import ERManager
import numpy as np


class ERTableWidgetItem:
    def __init__(self, fileName: str, description: str, idTag: str, name: str, downloaded: bool):
        self.item = QTableWidgetItem(name)
        self._checkBox = QCheckBox()
        self.checkBoxWidget = QWidget()
        l = QHBoxLayout()
        l.setAlignment(QtCore.Qt.AlignCenter)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self._checkBox)
        self.checkBoxWidget.setLayout(l)
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.name = name
        self.item.setToolTip('\n'.join([f'File Name: {self.fileName}', f'ID: {self.idTag}', f'Description: {self.description}']))
        if downloaded:
            self._checkBox.setCheckState(QtCore.Qt.Checked)
            self._checkBox.setEnabled(False)
        self._downloaded = downloaded

    @property
    def downloaded(self): return self._downloaded

    def isChecked(self):
        return self._checkBox.isChecked()


class ExplorerWindow(QDialog):
    def __init__(self, parent: QWidget, filePath: str):
        super().__init__(parent)
        self.filePath = filePath
        self.setWindowTitle("Extra Reflectance Manager")
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(self)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(self.displayInfo)
        self.table.setColumnCount(1)
        self.downloadButton = QPushButton("Download Checked Items")
        self.downloadButton.released.connect(self._cb(self._downloadCheckedItems))
        self.updateButton = QPushButton('Update Index')
        self.updateButton.released.connect(self._cb(self._updateIndex))
        self.buttons = [self.updateButton, self.downloadButton]
        self.layout().addWidget(self.table)
        self.layout().addWidget(self.downloadButton)
        self.layout().addWidget(self.updateButton)
        self._initialize(filePath)

    def _updateIndex(self):
        self.manager.download("index.json")
        self._initialize(self.filePath)

    def _initialize(self, filePath: str):
        self.manager = ERManager(filePath)
        self.table.setRowCount(0)
        self.table.setColumnCount(2)
        self.table.setColumnWidth(0, 10)
        self._items: List[ERTableWidgetItem] = []
        for item in self.manager.index['reflectanceCubes']:
            self._addItem(item)

    def _addItem(self, item: dict):
        tableItem = ERTableWidgetItem(fileName=item['fileName'], description=item['description'], idTag=item['idTag'], name=item['name'], downloaded=item['downloaded'])
        self._items.append(tableItem)
        self.table.setRowCount(len(self._items))
        self.table.setCellWidget(self.table.rowCount() - 1, 0, tableItem.checkBoxWidget)
        self.table.setItem(self.table.rowCount() - 1, 1, tableItem.item)

    def displayInfo(self, item: QTableWidgetItem):
        item = self._items[item.row()]
        message = QMessageBox.information(self, item.name, '\n\n'.join([f'FileName: {item.fileName}',
                                                                      f'ID Tag: {item.idTag}',
                                                                      f'Description: {item.description}']))

    def _downloadCheckedItems(self):
        for item in self._items:
            if item.isChecked() and not item.downloaded:
                # If the checkbox is enabled then it hasn't been downloaded yet. if it is checked then it should be downloaded
                self.manager.download(item.fileName)
        self._initialize(self.filePath)

    def _cb(self, func):
        def newfunc():
            try:
                [i.setEnabled(False) for i in self.buttons]
                func()
            finally:
                [i.setEnabled(True) for i in self.buttons]
        return newfunc
