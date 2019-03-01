# -*- coding: utf-8 -*-
"""
Created on Wed Feb 13 18:04:57 2019

@author: backman05
"""
import os

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QGridLayout, QDialog,
                             QLineEdit, QPushButton, QFileDialog, QCheckBox)


class WorkingDirDialog(QDialog):
    scanButtonPushed = QtCore.pyqtSignal(str, bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Working Directory")
        self.setLayout(QGridLayout())
        self.setModal(True)
        self.textLine = QLineEdit()
        self.browseButton = QPushButton(QtGui.QIcon(os.path.join('resources', 'folder.png')), '')
        self.scanButton = QPushButton('Scan!')
        self.recursiveCheckbox = QCheckBox("recursively scan subfolders")
        self.layout().addWidget(self.textLine, 0, 0, 1, 4)
        self.layout().addWidget(self.browseButton, 0, 5, 1, 1)
        self.layout().addWidget(self.recursiveCheckbox, 1, 0, 1, 2)
        self.layout().addWidget(self.scanButton, 1, 2, 1, 1)
        self.setFixedSize(400, 75)
        self.scanButton.released.connect(self.scanButtonPushed_)
        self.browseButton.released.connect(self.browseFile)

    def scanButtonPushed_(self):
        self.accept()
        self.scanButtonPushed.emit(self.textLine.text(), self.recursiveCheckbox.checkState() != 0)

    def browseFile(self):
        _ = QFileDialog(self)
        _.setFileMode(QFileDialog.DirectoryOnly)
        _.show()
        _.fileSelected.connect(self.textLine.setText)


if __name__ == '__main__':
    _ = WorkingDirDialog()
    _.show()
