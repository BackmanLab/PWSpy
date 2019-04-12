from PyQt5.QtWidgets import QDialog, QWidget, QTextEdit, QLineEdit


class IndexInfoForm(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.setModal(True)
        self.descriptionEdit = QTextEdit()
        self.nameEdit = QLineEdit()