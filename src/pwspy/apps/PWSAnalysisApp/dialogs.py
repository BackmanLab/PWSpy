# -*- coding: utf-8 -*-
"""
Created on Wed Feb 13 18:04:57 2019

@author: backman05
"""
import os
from glob import glob
from typing import Optional, List, Tuple

from pwspy.analysis.warnings import AnalysisWarning
from pwspy.apps import resources
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QGridLayout, QDialog,
                             QLineEdit, QPushButton, QFileDialog, QCheckBox,
                             QMessageBox, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem)

from pwspy.imCube import ICMetaData


class WorkingDirDialog(QDialog):
    directoryChanged = QtCore.pyqtSignal()

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
        self.directory = self.textLine.text()
        self.directoryChanged.emit(self.directory)
        recursive = self.recursiveCheckbox.checkState() != 0
        pattern = [os.path.join('**', 'Cell[0-9]*')] if recursive else ['Cell[0-9]*']
        files = []
        for patt in pattern:
            files.extend(glob(os.path.join(self.directory, patt), recursive=recursive))
        if len(files) == 0:
            QMessageBox.information(self, "Hmm", "No PWS files were found.")
        else:
            nums = []
            newFiles = []
            for f in files:
                try:
                    nums.append(int(os.path.split(f)[-1].split('Cell')[-1]))
                    newFiles.append(f)
                except ValueError:
                    pass
            nums, files = zip(*sorted(zip(nums, newFiles)))
            self.parent().cellSelector.clearCells()
            for i, (num, f) in enumerate(zip(nums, files)):
                self.parent().cellSelector.addCell(f, self.directory)
            self.parent().cellSelector.updateFilters()
            self.accept()

    def browseFile(self):
        _ = QFileDialog.getExistingDirectory(self, 'Working Directory', self.directory)
        if _ != '':
            self.directory = _
            self.textLine.setText(self.directory)


class AnalysisSummaryDisplay(QWidget):
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        layout = QVBoxLayout
        self.warnList = QTreeWidget(self)
        layout.addWidget(self.warnList)
        self.setLayout(layout)

    def addWarnings(self, warnings: List[Tuple[List[AnalysisWarning], ICMetaData]]):
        for cellWarns, cell in warnings:
            item = QTreeWidgetItem(self.warnList)
            item.setText(0, cell.filePath)
            for warn in cellWarns:
                subItem = QTreeWidgetItem(item)
                subItem.setText(0, warn.shortMsg)
                subItem.setToolTip(0, warn.longMsg)

    def clearWarnings(self):
        self.warnList.clear()


if __name__ == '__main__':
    _ = WorkingDirDialog()
    _.show()
