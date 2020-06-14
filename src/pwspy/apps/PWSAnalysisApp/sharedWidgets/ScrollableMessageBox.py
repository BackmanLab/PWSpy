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

from __future__ import annotations

import sys

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox, QScrollArea, QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
import typing


class ScrollableMessageBox(QMessageBox):
    def __init__(self, icon: QMessageBox.Icon, title: str, text: str, buttons: QMessageBox.StandardButtons = QMessageBox.NoButton, parent: QWidget = None,
                f: QtCore.Qt.WindowFlags = QtCore.Qt.Dialog | QtCore.Qt.MSWindowsFixedSizeDialogHint):
        QMessageBox.__init__(self, icon, title, "", buttons, parent, f)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self.content = QWidget()
        lay = QVBoxLayout()
        self.content.setLayout(lay)
        scroll.setWidget(self.content)
        scroll.setStyleSheet("QScrollArea{min-width:300 px; min-height: 200px}")
        label = QLabel(text, self)
        label.setWordWrap(True)
        lay.addWidget(label)
        lay.setAlignment(QtCore.Qt.AlignTop)
        self.layout().replaceWidget(self.layout().itemAt(2).widget(), scroll)

    @staticmethod
    def question(parent: QWidget, title: str, text: str, buttons: typing.Union[QMessageBox.StandardButtons, QMessageBox.StandardButton] = QMessageBox.Yes|QMessageBox.No,
                 defaultButton: QMessageBox.StandardButton = QMessageBox.Yes) -> QMessageBox.StandardButton:
        scr = ScrollableMessageBox(QMessageBox.Question, title, text, buttons, parent)
        scr.setModal(True)
        scr.exec()
        return scr.result()

if __name__ == "__main__":
    string = ""
    for i in range(10):
        string += str(i) + " "
    app = QApplication(sys.argv)
    button = QPushButton("GO")
    scr = ScrollableMessageBox.question(button, "Test Title", string)
    print(scr)
    sys.exit(app.exec())