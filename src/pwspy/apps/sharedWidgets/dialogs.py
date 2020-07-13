# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

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
