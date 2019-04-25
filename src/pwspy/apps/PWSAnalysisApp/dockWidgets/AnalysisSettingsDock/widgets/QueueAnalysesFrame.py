from typing import List, Optional, Tuple

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint

from PyQt5.QtWidgets import QListWidgetItem, QWidget, QScrollArea, QListWidget, QMessageBox, QMenu, QAction

from pwspy.analysis import AnalysisSettings
from pwspy.apps.PWSAnalysisApp.dockWidgets import AnalysisSettingsDock
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from pwspy.imCube import ICMetaData, CameraCorrection
import json


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
        self.setWidgetResizable(True)

    @property
    def analyses(self) -> List[Tuple[str, AnalysisSettings, List[ICMetaData], ICMetaData, CameraCorrection]]:
        items: List[AnalysisListItem] = [self.listWidget.item(i) for i in range(self.listWidget.count())]
        return [(item.name, item.settings, item.cells, item.reference, item.cameraCorrection)  for item in items]

    def addAnalysis(self, analysisName: str, cameraCorrection: CameraCorrection, settings: AnalysisSettings,
                    reference: ICMetaData, cells: List[ICMetaData]):
        if reference is None:
            QMessageBox.information(self, '!', f'Please select a reference Cell.')
            return
        if analysisName == '':
            QMessageBox.information(self, '!', "Please give your analysis a name.")
            return
        for i in range(self.listWidget.count()):
            if self.listWidget.item(i).name == analysisName:
                QMessageBox.information(self, '!', f'Analysis {analysisName} already exists.')
                return
        item = AnalysisListItem(cameraCorrection, settings, reference, cells, analysisName, self.listWidget) #the item is automatically loaded ot the list here.

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        deleteAction = QAction("Delete", self)
        deleteAction.triggered.connect(self.deleteSelected)
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(point))

    def deleteSelected(self):
        for i in self.listWidget.selectedItems():
            self.listWidget.takeItem(self.listWidget.row(i))

