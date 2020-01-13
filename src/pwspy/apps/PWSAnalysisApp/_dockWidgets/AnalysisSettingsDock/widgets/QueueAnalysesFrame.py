from __future__ import annotations
from typing import List, Optional, Tuple
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QListWidgetItem, QWidget, QScrollArea, QListWidget, QMessageBox, QMenu, QAction, QDialog, QGridLayout, QPushButton

from pwspy.analysis import AbstractAnalysisSettings, AnalysisTypes
from pwspy.analysis.dynamics._analysisSettings import DynamicsAnalysisSettings
from pwspy.analysis.pws import PWSAnalysisSettings
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock import DynamicsSettingsFrame
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._PWSSettingsFrame import PWSSettingsFrame
from pwspy.dataTypes import AcqDir
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import CameraCorrection
    from pwspy.apps.PWSAnalysisApp._dockWidgets import AnalysisSettingsDock


class AnalysisListItem(QListWidgetItem):
    def __init__(self, cameraCorrection: CameraCorrection, settings: AbstractAnalysisSettings, reference: AcqDir, cells: List[AcqDir], analysisName: str,
                 parent: Optional[QWidget] = None):
        if isinstance(settings, PWSAnalysisSettings):
            prefix = "PWS: "
            self.type = AnalysisTypes.PWS
        elif isinstance(settings, DynamicsAnalysisSettings):
            prefix = "DYN: "
            self.type = AnalysisTypes.DYN
        else:
            raise TypeError(f"AnalysisListItem recieve unrecognized analyis settings object of type: {type(settings)}")
        super().__init__(prefix + analysisName, parent)
        self.cameraCorrection = cameraCorrection
        self.settings = settings
        self.reference = reference
        self.cells = cells
        self.name = analysisName


class QueuedAnalysesFrame(QScrollArea):
    def __init__(self, parent: AnalysisSettingsDock):
        super().__init__()
        self.parent = parent
        self.listWidget = QListWidget()
        self.setWidget(self.listWidget)
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)
        self.listWidget.setMinimumHeight(30)
        self.setWidgetResizable(True)
        self.listWidget.itemDoubleClicked.connect(self.displayItemSettings)
        self.listWidget.itemClicked.connect(self.highlightAssociatedCells)

    @property
    def analyses(self) -> List[Tuple[str, AbstractAnalysisSettings, List[AcqDir], AcqDir, CameraCorrection, AnalysisListItem]]:
        items: List[AnalysisListItem] = [self.listWidget.item(i) for i in range(self.listWidget.count())]
        return [(item.name, item.settings, item.cells, item.reference, item.cameraCorrection, item) for item in items]

    def addAnalysis(self, analysisName: str, cameraCorrection: CameraCorrection, settings: AbstractAnalysisSettings,
                    reference: AcqDir, cells: List[AcqDir]):
        if reference is None:
            QMessageBox.information(self, '!', 'Please select a reference Cell.')
            return
        if analysisName == '':
            QMessageBox.information(self, '!', "Please give your analysis a name.")
            return
        if len(cells) == 0:
            QMessageBox.information(self, '!', 'Please select cells to analyse.')
            return
        item = AnalysisListItem(cameraCorrection, settings, reference, cells, analysisName, self.listWidget) #the item is automatically added to the list here.

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        deleteAction = QAction("Delete", self)
        deleteAction.triggered.connect(self.deleteSelected)
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(point))

    def deleteSelected(self):
        for i in self.listWidget.selectedItems():
            self.listWidget.takeItem(self.listWidget.row(i))

    def highlightAssociatedCells(self, item: AnalysisListItem):
        # Highlight relevant cells
        self.parent.selector.setHighlightedCells(item.cells)
        self.parent.selector.setHighlightedReference(item.reference)

    def displayItemSettings(self, item: AnalysisListItem):
        # Open a dialog
        # message = QMessageBox.information(self, item.name, json.dumps(item.settings.asDict(), indent=4))
        d = QDialog(self.parent, (QtCore.Qt.WindowTitleHint | QtCore.Qt.Window))
        d.setModal(True)
        d.setWindowTitle(item.name)
        l = QGridLayout()
        if item.type == AnalysisTypes.PWS:
            settingsFrame = PWSSettingsFrame(self.parent.erManager)
        elif item.type == AnalysisTypes.DYN:
            settingsFrame = DynamicsSettingsFrame(self.parent.erManager)
        else:
            raise TypeError(f"Analysis of type {item.type} is not supported.")
        settingsFrame.loadFromSettings(item.settings)
        settingsFrame.loadCameraCorrection(item.cameraCorrection)
        settingsFrame._analysisNameEdit.setText(item.name)
        settingsFrame._analysisNameEdit.setEnabled(False)  # Don't allow changing the name.

        okButton = QPushButton("OK")
        okButton.released.connect(d.accept)

        l.addWidget(settingsFrame, 0, 0, 1, 1)
        l.addWidget(okButton, 1, 0, 1, 1)
        d.setLayout(l)
        d.show()
        d.exec()
        try:
            item.settings = settingsFrame.getSettings()
            item.cameraCorrection = settingsFrame.getCameraCorrection()
        except Exception as e:
            QMessageBox.warning(self.parent, 'Oh No!', str(e))



