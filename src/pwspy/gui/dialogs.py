# -*- coding: utf-8 -*-
"""
Created on Wed Feb 13 18:04:57 2019

@author: backman05
"""
import os
from glob import glob
from . import resources
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QGridLayout, QDialog,
                             QLineEdit, QPushButton, QFileDialog, QCheckBox,
                             QMessageBox)


class WorkingDirDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent,
                         QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowCloseButtonHint)  # Construct without a question mark button
        self.setWindowTitle("Working Directory")
        layout = QGridLayout()
        self.setModal(True)
        self.textLine = QLineEdit()
        self.browseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.png')), '')
        self.scanButton = QPushButton('Scan!')
        self.recursiveCheckbox = QCheckBox("recursively scan subfolders")
        layout.addWidget(self.textLine, 0, 0, 1, 4)
        layout.addWidget(self.browseButton, 0, 5, 1, 1)
        layout.addWidget(self.recursiveCheckbox, 1, 0, 1, 2)
        layout.addWidget(self.scanButton, 1, 2, 1, 1)
        self.setLayout(layout)
        self.setFixedSize(400, 75)
        self.scanButton.released.connect(self._scanButtonPushed)
        self.browseButton.released.connect(self.browseFile)
        self.directory = os.path.expanduser('~')

    def _scanButtonPushed(self):
        recursive = self.recursiveCheckbox.checkState() != 0
        pattern = [os.path.join('**', 'Cell*')] if recursive else ['Cell*']
        files = []
        for patt in pattern:
            files.extend(glob(os.path.join(self.directory, patt), recursive=recursive))
        if len(files) == 0:
            QMessageBox.information(self, "Hmm", "No PWS files were found.")
        else:
            _, files = zip(*sorted([(int(f.split('Cell')[-1]), f) for f in files]))
            self.parent().cellSelector.clearCells()
            self.progressBar = QProgressDialog('Scanning', 'Cancel', 0, len(files), self)
            self.progressBar.setAutoClose(True)
            self.progressBar.setWindowModality(QtCore.Qt.WindowModal)
            for i, f in enumerate(files):
                self.progressBar.setValue(i)
                self.parent().cellSelector.addCell(f, self.directory)
                if self.progressBar.wasCanceled():
                    break
            self.parent().cellSelector.updateFilters()
            self.progressBar.reset()

    def browseFile(self):
        _ = QFileDialog.getExistingDirectory(self, 'Working Directory', self.directory)
        if _ != '':
            self.directory = _
            self.textLine.setText(self.directory)

if __name__ == '__main__':
    _ = WorkingDirDialog()
    _.show()
