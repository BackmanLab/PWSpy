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

# -*- coding: utf-8 -*-
"""
Created on Wed Feb 13 18:04:57 2019

@author: Nick Anthony
"""
from __future__ import annotations
import os
from glob import glob
from pwspy.apps import resources
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QGridLayout, QDialog,
                             QLineEdit, QPushButton, QFileDialog, QCheckBox,
                             QMessageBox, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QApplication)

import typing

from pwspy.apps.PWSAnalysisApp._dockWidgets.ResultsTableDock import ConglomerateCompilerResults

if typing.TYPE_CHECKING:
    from typing import Optional, List, Tuple
    from pwspy.dataTypes import ICMetaData
    from pwspy.analysis.compilation import PWSRoiCompilationResults
    from pwspy.analysis.pws import PWSAnalysisSettings
    from pwspy.analysis.warnings import AnalysisWarning


class WorkingDirDialog(QDialog):
    directoryChanged = QtCore.pyqtSignal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent,
                         QtCore.Qt.WindowTitleHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowCloseButtonHint)  # Construct without a question mark button
        self.setWindowTitle("Working Directory")
        layout = QGridLayout()
        self.setModal(True)
        self.textLine = QLineEdit()
        self.browseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.svg')), '')
        self.scanButton = QPushButton('Scan!')
        self.recursiveCheckbox = QCheckBox("recursively scan subfolders")
        self.recursiveCheckbox.setChecked(True)
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
            self.directoryChanged.emit(self.directory, list(files))
            self.accept()

    def browseFile(self):
        _ = QFileDialog.getExistingDirectory(self, 'Working Directory', self.directory)
        if _ != '':
            self.directory = _
            self.textLine.setText(self.directory)

    def show(self):
        super().show()
        self.browseFile()


class AnalysisSummaryDisplay(QDialog):
    def __init__(self, parent: Optional[QWidget], warnings: List[Tuple[List[AnalysisWarning], ICMetaData]], analysisName: str = '', analysisSettings: PWSAnalysisSettings = None):
        super().__init__(parent=parent)
        self.analysisName = analysisName
        self.analysisSettings = analysisSettings
        layout = QVBoxLayout()
        self.settingsButton = QPushButton("Settings", self)
        self.settingsButton.released.connect(self._displaySettings)
        self.warnList = QTreeWidget(self)
        self.warnList.setHeaderHidden(True)
        layout.addWidget(self.settingsButton)
        layout.addWidget(self.warnList)
        self.setLayout(layout)
        self._addWarnings(warnings)
        self.setWindowTitle(f"Analysis Summary: {analysisName}")
        self.show()

    def _addWarnings(self, warnings: List[Tuple[List[AnalysisWarning],ICMetaData]]):
         for cellWarns, cell in warnings:
            item = QTreeWidgetItem(self.warnList)
            item.setText(0, cell.filePath)
            for warn in cellWarns:
                subItem = QTreeWidgetItem(item)
                subItem.setText(0, warn.shortMsg)
                subItem.setToolTip(0, warn.longMsg)

    def clearWarnings(self):
        self.warnList.clear()

    def _displaySettings(self):
        if self.analysisSettings is not None:
            msgBox = QMessageBox.information(self, self.analysisName, self.analysisSettings.toJsonString())

if __name__ == '__main__':
    _ = WorkingDirDialog()
    _.show()
