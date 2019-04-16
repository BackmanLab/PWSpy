from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QMessageBox, QWidget, QCheckBox, QVBoxLayout, \
    QPushButton, QLineEdit, QComboBox, QGridLayout, QLabel, QDialogButtonBox

from .manager import ERManager
import numpy as np


class ERTableWidgetItem(QTableWidgetItem):
    def __init__(self, fileName: str, description: str, idTag: str, name: str):
        super().__init__(name)
        self.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.name = name
        self.setToolTip('\n'.join([f'File Name: {self.fileName}', f'ID: {self.idTag}', f'Description: {self.description}']))

    def setEnabled(self, enabled: bool):
        if enabled:
            flags = self.flags() | QtCore.Qt.ItemIsEnabled
        else:
            flags = self.flags() & ~QtCore.Qt.ItemIsEnabled
        self.setFlags(flags)

    def isEnabled(self) -> bool:
        return bool(self.flags() & QtCore.Qt.ItemIsEnabled)


class ExplorerWindow(QDialog):
    def __init__(self, parent: QWidget, filePath: str):
        super().__init__(parent)
        self.filePath = filePath
        self.setWindowTitle("Extra Reflectance Manager")
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(self)
        self.table.itemClicked.connect(self.toggleCheck)
        # self.table.itemDoubleClicked.connect(self.displayInfo)
        self.table.setColumnCount(1)
        self.downloadButton = QPushButton("Download Checked Items")
        self.downloadButton.released.connect(self._downloadCheckedItems)
        self.updateButton = QPushButton('Update Index')
        self.updateButton.released.connect(lambda: self.manager.download("index.json"))
        self.layout().addWidget(self.table)
        self.layout().addWidget(self.downloadButton)
        self.layout().addWidget(self.updateButton)
        self._initialize(filePath)

    def _initialize(self, filePath: str):
        self.manager = ERManager(filePath)
        self.table.setRowCount(0)
        self._items = []
        for item in self.manager.index['reflectanceCubes']:
            self._addItem(item)

    def _addItem(self, item: dict):
        tableItem = ERTableWidgetItem(fileName=item['fileName'], description=item['description'], idTag=item['idTag'], name=item['name'])
        self._items.append(tableItem)
        self.table.setRowCount(len(self._items))
        self.table.setItem(self.table.rowCount()-1, 0, tableItem)
        if item['downloaded']:
            tableItem.setCheckState(QtCore.Qt.Checked)
            tableItem.setEnabled(False)
        else:
            tableItem.setCheckState(QtCore.Qt.Unchecked)

    # def displayInfo(self, item: ERTableWidgetItem):
    #     message = QMessageBox.information(self, item.name, '\n'.join([item.fileName, item.idTag, item.description]))

    def _downloadCheckedItems(self):
        for i in range(self.table.rowCount()):
            item: ERTableWidgetItem = self.table.item(i, 0)
            if item.isEnabled() and item.checkState():
                # If the checkbox is enabled then it hasn't been downloaded yet. if it is checked then it should be downloaded
                self.manager.download(item.fileName)
        self._initialize(self.filePath)

    def toggleCheck(self, item: ERTableWidgetItem):
        state = 0 if item.checkState() else 2
        item.setCheckState(state)