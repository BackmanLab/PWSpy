from typing import List, Optional

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint

from PyQt5.QtWidgets import QListWidgetItem, QWidget, QScrollArea, QListWidget, QMessageBox, QMenu, QAction

from pwspy import CameraCorrection
from pwspy.analysis import AnalysisSettings
from pwspy.imCube.ICMetaDataClass import ICMetaData


class AnalysisListItem(QListWidgetItem):
    def __init__(self, cameraCorrection: CameraCorrection, settings: AnalysisSettings, reference: ICMetaData, cells: List[ICMetaData], label: str,
                 parent: Optional[QWidget] = None):
        super().__init__(label, parent)
        self.cameraCorrection = cameraCorrection
        self.settings = settings
        self.reference = reference
        self.cells = cells


class QueuedAnalysesFrame(QScrollArea):
    def __init__(self):
        super().__init__()
        self.listWidget = QListWidget()
        self.setWidget(self.listWidget)
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)
        #self.listWidget.itemDoubleClicked.connect( # TODO display settings)

    def addAnalysis(self, cameraCorrection: CameraCorrection, settings: AnalysisSettings, reference: ICMetaData, cells: List[ICMetaData]):
        if reference is None:
            QMessageBox.information(self, '!', f'Please select a reference Cell.')
            return
        item = AnalysisListItem(cameraCorrection, settings, reference, cells, 'BlahBlah', self.listWidget)
        self.listWidget.addItem(item)

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        deleteAction = QAction("Delete", self)
        deleteAction.triggered.connect(self.deleteSelected)
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(point))