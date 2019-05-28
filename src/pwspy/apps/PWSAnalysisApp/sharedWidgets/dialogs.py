from PyQt5.QtWidgets import QDialog, QWidget, QGridLayout, QLabel
from qtpy import QtCore


class BusyDialog(QDialog):
    def __init__(self, parent: QWidget, msg: str):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        l = QGridLayout()
        l.addWidget(QLabel(msg))
        self.setLayout(l)
        self.show()

