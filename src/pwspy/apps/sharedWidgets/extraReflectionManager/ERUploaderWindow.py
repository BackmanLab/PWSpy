from __future__ import annotations
from typing import Optional

from PyQt5.QtWidgets import QDialog, QWidget, QHBoxLayout, QPushButton, QAbstractItemView, QTableWidget, QVBoxLayout


class ERUploaderWindow(QDialog):
    def __init__(self, manager: ERManager, parent: Optional[QWidget] = None):
        self._manager = manager
        self._selectedId: str = None
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Extra Reflectance File Manager")
        self.setLayout(QVBoxLayout())
        self.table = QTableWidget(self)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(self.displayInfo)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setRowCount(0)
        self.table.setColumnCount(3)
        self.table.setSortingEnabled(True)
        self.table.setHorizontalHeaderLabels([" ", "System", "Date"])
        self.table.setColumnWidth(0, 10)

        self.uploadButton = QPushButton("Upload to Drive")
        self.uploadButton.released.connect(self._updateGDrive)
        self.refreshButton = QPushButton('Refresh')
        self.refreshButton.setToolTip("Rescan the files in the applications data directory.")
        self.refreshButton.released.connect(self._rescan)
        self.layout().addWidget(self.table)
        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.uploadButton)
        l.addWidget(self.refreshButton)
        w = QWidget()
        w.setLayout(l)
        self.layout().addWidget(w)
        self._initialize()

    def displayInfo(self):
        pass
    def _updateGDrive(self):
        pass
    def _rescan(self):
        pass
    def _initialize(self):
        pass