import json
import shutil

from PyQt5 import QtGui
from PyQt5.QtWidgets import QDialog, QFileDialog, QWidget, QLineEdit, QPushButton, QLabel, QGridLayout, QMessageBox

from pwspy.apps import resources
from pwspy.dataTypes import ICMetaData
from typing import List
import os
import random

class Blinder:
    def __init__(self, cells: List[ICMetaData], homeDir: str, outDir: str):
        indexPath = os.path.join(homeDir, 'blindedIndex.json')
        if os.path.exists(indexPath):
            raise ValueError(f"A `blindedIndex.json` file already exists in {homeDir}.")
        if os.path.exists(outDir):
            raise ValueError(f"The output directory, {outDir}, already exists.")
        os.mkdir(outDir)
        try:
            paths = [c.filePath for c in cells]
            nums = list(range(1, len(paths)+1))
            assert len(nums) == len(paths)
            random.shuffle(nums)  # nums is now a random list of non-repeating numbers from one up to the number of cells.
            d = {'outputDirectory': outDir}
            d['index'] = []
            for path, num in zip(paths, nums):
                newPath = os.path.join(outDir, f'Cell{num}')
                os.symlink(path, newPath)
                d['index'].append({path: f'Cell{num}'})
        except Exception as e:
            shutil.rmtree(outDir)
            raise e
        with open(indexPath, 'w') as f:
            json.dump(d, f)


class BlinderDialog(QDialog):
    def __init__(self, parent: QWidget, homeDir: str, cells: List[ICMetaData]):
        self.parent = parent
        self.homeDir = homeDir
        self.cells = cells
        super().__init__(self.parent)
        self.setModal(True)
        self.pathEdit = QLineEdit(self)
        self.browseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.svg')), '')
        self.browseButton.released.connect(self.getPath)
        self.slashLabel = QLabel('/', self)
        self.folderNameEdit = QLineEdit(self)
        self.okButton = QPushButton('Ok', self)
        self.okButton.released.connect(self.accept)
        self.okButton.setMaximumWidth(100)
        layout = QGridLayout(self)
        layout.addWidget(self.browseButton, 0, 0)
        layout.addWidget(self.pathEdit, 0, 1)
        layout.addWidget(self.slashLabel, 0, 2)
        layout.addWidget(self.folderNameEdit, 0, 3)
        layout.addWidget(self.okButton, 1, 1, 1, 2)

        newDir = self.getPath()
        self.pathEdit.setText(newDir)

    def getPath(self) -> str:
        newDir = QFileDialog.getExistingDirectory(self.parent, "Select location for new blinded directory", self.pathEdit.text())
        return newDir

    def accept(self) -> None:
        try:
            if self.folderNameEdit.text() == '':
                raise ValueError("Folder name must be specified.")
            outDir = os.path.join(self.pathEdit.text(), self.folderNameEdit.text())
            b = Blinder(self.cells, self.homeDir, outDir)
            super().accept()
        except Exception as e:
            msg = QMessageBox.warning(self, 'Uh Oh', str(e))
