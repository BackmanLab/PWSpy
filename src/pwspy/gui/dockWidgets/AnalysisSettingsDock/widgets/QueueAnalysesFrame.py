from typing import List, Optional

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint

from PyQt5.QtWidgets import QListWidgetItem, QWidget, QScrollArea, QListWidget, QMessageBox, QMenu, QAction, QTextEdit

from pwspy import CameraCorrection
from pwspy.analysis import AnalysisSettings
from pwspy.imCube.ICMetaDataClass import ICMetaData


class AnalysisListItem(QListWidgetItem):
    def __init__(self, cameraCorrection: CameraCorrection, settings: AnalysisSettings, reference: ICMetaData, cells: List[ICMetaData], analysisName: str,
                 parent: Optional[QWidget] = None):
        super().__init__(analysisName, parent)
        self.cameraCorrection = cameraCorrection
        self.settings = settings
        self.reference = reference
        self.cells = cells
        self.name = analysisName


class QueuedAnalysesFrame(QScrollArea):
    def __init__(self):
        super().__init__()
        self.listWidget = QListWidget()
        self.setWidget(self.listWidget)
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)
        self.listWidget.itemDoubleClicked.connect(self.displayItemSettings)
        self.listWidget.currentItemChanged.connect(self.highlightItemCells)
        self.setWidgetResizable(True)

    def addAnalysis(self, analysisName: str, cameraCorrection: CameraCorrection, settings: AnalysisSettings, reference: ICMetaData, cells: List[ICMetaData]):
        if reference is None:
            QMessageBox.information(self, '!', f'Please select a reference Cell.')
            return
        item = AnalysisListItem(cameraCorrection, settings, reference, cells, analysisName, self.listWidget)
        self.listWidget.addItem(item)

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        deleteAction = QAction("Delete", self)
        deleteAction.triggered.connect(self.deleteSelected)
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(point))

    def deleteSelected(self):
        for i in self.listWidget.selectedItems():
            self.listWidget.takeItem(self.listWidget.row(i))

    def displayItemSettings(self, item: AnalysisListItem):
        message = QMessageBox.information(self, item.name, item.settings.toJsonString())

    def highlightItemCells(self, currentItem: AnalysisListItem, oldItem: AnalysisListItem):
        pass # Todo

