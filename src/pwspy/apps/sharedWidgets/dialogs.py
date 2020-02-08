from PyQt5.QtWidgets import QDialog, QWidget, QGridLayout, QLabel, QProgressBar, QApplication
from PyQt5 import QtCore


class BusyDialog(QDialog):
    def __init__(self, parent: QWidget, msg: str, progressBar: bool = False):
        super().__init__(parent, QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        layout = QGridLayout()
        label = QLabel(msg)
        font = label.font()
        font.setBold(True)
        font.setPointSize(18)
        label.setFont(font)
        layout.addWidget(label)
        self.progressBar = QProgressBar() if progressBar else None
        if self.progressBar:
            layout.addWidget(self.progressBar)
        self.setLayout(layout)
        self.show()

    def setProgress(self, percent: int):
        if self.progressBar:
            self.progressBar.setValue(percent)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    dlg = BusyDialog(None, "Busy, Please Wait")
    sys.exit(app.exec())
