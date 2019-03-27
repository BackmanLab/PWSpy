from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QMessageBox, QWidget, QCheckBox, QVBoxLayout, \
    QPushButton, QLineEdit, QComboBox, QGridLayout, QLabel, QDialogButtonBox

from .manager import ERManager

class ERTableWidgetItem(QTableWidgetItem):
    def __init__(self, fileName: str, description: str, idTag: str, name: str):
        super().__init__(name)
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.name = name


class ExplorerWindow(QDialog):
    def __init__(self, parent: QWidget, filePath: str):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(self)
        self.table.itemDoubleClicked.connect(self.displayInfo)
        self.table.setColumnCount(2)
        self.updateButton = QPushButton('Update Index')
        self.updateButton.released.connect(lambda: self.manager.download("index.json"))
        self.layout().addWidget(self.table)
        self.layout().addWidget(self.updateButton)
        self._initialize(filePath)

    def _initialize(self, filePath: str):
        self.manager = ERManager(filePath)
        self.table.setRowCount(0)
        self._items = []
        for item in self.manager.index['reflectionCubes']:
            self._addItem(item)

    def _addItem(self, item: dict):
        tableItem = ERTableWidgetItem(fileName=item['fileName'], description=item['description'], idTag=item['idTag'], name=item['name'])
        self._items.append(tableItem)
        self.table.setRowCount(len(self._items))
        self.table.setItem(self.table.rowCount()-1, 0, tableItem)
        checkBox = QCheckBox(self.table)
        checkBox.setCheckState(item['downloaded'])
        self.table.setCellWidget(self.table.rowCount()-1, 1, checkBox)

    def displayInfo(self, item: ERTableWidgetItem):
        message = QMessageBox.information(self, item.name, '\n'.join([item.fileName, item.idTag, item.description]))