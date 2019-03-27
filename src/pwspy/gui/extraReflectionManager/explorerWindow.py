from PyQt5 import QtCore
from PyQt5.QtWidgets import QDialog, QTableWidget, QTableWidgetItem, QMessageBox, QWidget, QCheckBox, QVBoxLayout, \
    QPushButton, QLineEdit, QComboBox, QGridLayout, QLabel, QDialogButtonBox

from .manager import ERManager


class LoginDialog(QDialog):
    acceptLogin = QtCore.pyqtSignal(str, str)
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setUpGUI()
        self.setWindowTitle("User Login")
        self.setModal(True)

    def setUpGUI(self):
        formGridLayout = QGridLayout()

        self.editUsername = QLineEdit(self)
        # initialize the password field so that it does not echo characters
        self.editPassword = QLineEdit(self)
        self.editPassword.setEchoMode( QLineEdit.Password )

        # initialize the labels
        labelUsername = QLabel(self)
        labelPassword = QLabel(self)
        labelUsername.setText("Username")
        labelUsername.setBuddy(self.editUsername)
        labelPassword.setText("Password")
        labelPassword.setBuddy(self.editPassword)

        # initialize buttons
        buttons = QDialogButtonBox(self)
        buttons.addButton( QDialogButtonBox.Ok )
        buttons.addButton( QDialogButtonBox.Cancel )
        buttons.button( QDialogButtonBox.Ok ).setText("Login")
        buttons.button( QDialogButtonBox.Cancel ).setText("Abort")

        # connects slots
        buttons.button(QDialogButtonBox.Cancel).released.connect(self.close)
        buttons.button(QDialogButtonBox.Ok).released.connect(self.slotAcceptLogin)

        # place components into the dialog
        formGridLayout.addWidget(labelUsername, 0, 0)
        formGridLayout.addWidget(self.editUsername, 0, 1)
        formGridLayout.addWidget(labelPassword, 1, 0)
        formGridLayout.addWidget(self.editPassword, 1, 1)
        formGridLayout.addWidget(buttons, 2, 0, 1, 2)
        self.setLayout(formGridLayout)

    def slotAcceptLogin(self):
        username = self.editUsername.text()
        password = self.editPassword.text()
        self.acceptLogin.emit(username, password)
        self.close()


class ERTableWidgetItem(QTableWidgetItem):
    def __init__(self, fileName: str, description: str, idTag: str, name: str):
        super().__init__(name)
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.name = name

class explorerWindow(QDialog):
    def __init__(self, parent: QWidget, filePath: str):
        super().__init__(parent)
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(self)
        self.table.itemDoubleClicked.connect(self.displayInfo)
        self.table.setColumnCount(2)
        self.updateButton = QPushButton('Update Index')
        self.updateButton.released.connect(lambda: self.attemptDownload("index.json"))
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

    def attemptDownload(self, fileName: str):
        if self.manager.auth is None:
            loginWindow = LoginDialog(self)
            loginWindow.acceptLogin.connect(lambda u, p: [self.manager.setAuth(u, p), self.attemptDownload(fileName)]) # retry. This seems sketchy
            return
        else:
            self.manager.download(fileName)
