from PyQt5.QtWidgets import QDialog, QWidget, QTextEdit, QLineEdit, QGridLayout, QLabel, QPushButton


class IndexInfoForm(QDialog):
    def __init__(self, name, idTag, parent: QWidget = None):
        super().__init__(parent=parent)
        self.description = None
        self.setModal(False)
        self.setWindowTitle(name)
        self.descriptionEdit = QTextEdit()
        self.okButton = QPushButton('OK!')
        self.okButton.released.connect(self.accept)
        layout = QGridLayout()
        layout.addWidget(QLabel("Description:", parent=self), 0, 0, 1, 1)
        layout.addWidget(self.descriptionEdit, 1, 0, 4, 4)
        layout.addWidget(QLabel(f"Name: {name}", self), 5, 0, 1, 1)
        layout.addWidget(QLabel(f"idTag: {idTag}", self), 5, 1, 1, 1)
        layout.addWidget(self.okButton, 5, 3, 1, 1)
        self.setLayout(layout)

    def accept(self) -> None:
        self.description = self.descriptionEdit.toPlainText()
        super().accept()
