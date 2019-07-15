from PyQt5.QtWidgets import QDialog, QWidget, QGridLayout, QLabel, QProgressBar
from PyQt5 import QtCore


class BusyDialog(QDialog):
    def __init__(self, parent: QWidget, msg: str, progressBar: bool = None):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        l = QGridLayout()
        l.addWidget(QLabel(msg))
        self.progressBar = QProgressBar() if progressBar else None
        if self.progressBar:
            l.addWidget(self.progressBar)
        self.setLayout(l)
        self.show()

    def setProgress(self, percent: int):
        if self.progressBar:
            self.progressBar.setValue(percent)

