from __future__ import annotations
import json
from typing import Tuple, List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, \
    QVBoxLayout, QPushButton, QSplitter, QMessageBox, QDialog, QGridLayout, QApplication

from pwspy.dataTypes import CameraCorrection
from pwspy.analysis import AnalysisSettings

from pwspy.dataTypes._ExtraReflectanceCubeClass import ERMetadata
from .widgets.QueueAnalysesFrame import AnalysisListItem, QueuedAnalysesFrame
from .widgets.SettingsFrame import SettingsFrame

import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp._dockWidgets import CellSelectorDock
    from pwspy.dataTypes import ImCube





class AnalysisSettingsDock(QDockWidget):
    def __init__(self, cellSelector: CellSelectorDock, erManager):
        super().__init__("Settings")
        self.erManager = erManager
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.selector = cellSelector
        self.setObjectName('AnalysisSettingsDock')  # needed for restore state to work
        widg = QWidget()
        widg.setLayout(QVBoxLayout())
        self.settingsFrame = SettingsFrame(self.erManager)
        widg.layout().addWidget(self.settingsFrame)
        self.addAnalysisButton = QPushButton("Add Analysis")
        widg.layout().addWidget(self.addAnalysisButton)

        self.analysesQueue = QueuedAnalysesFrame()
        self.analysesQueue.listWidget.itemDoubleClicked.connect(self.displayItemSettings)

        widg.layout().addWidget(self.analysesQueue)
        self.analysesQueue.setFixedHeight(50)
        widg.setMinimumHeight(200)
        widg.setMaximumWidth(self.settingsFrame.minimumWidth()+10)

        self.addAnalysisButton.released.connect(self.addAnalysis)
        self.setWidget(widg)

    def addAnalysis(self):
        try:
            camCorr = self.settingsFrame.getCameraCorrection()
            settings = self.settingsFrame.getSettings()
        except Exception as e:
            QMessageBox.information(self, 'Hold on', str(e))
            return
        self.analysesQueue.addAnalysis(self.settingsFrame.analysisName, camCorr, settings,
                                       self.selector.getSelectedReferenceMeta(),
                                       self.selector.getSelectedCellMetas())

    def loadFromSettings(self, settings: AnalysisSettings):
        self.settingsFrame.loadFromSettings(settings)

    def getAnalysisName(self):
        return self.settingsFrame.analysisName

    def getListedAnalyses(self) -> List[Tuple[str, AnalysisSettings, List[ImCube.ICMetaData], ImCube.ICMetaData, CameraCorrection, ERMetadata]]:
        return self.analysesQueue.analyses

    def displayItemSettings(self, item: AnalysisListItem):
        # Highlight relevant cells
        self.selector.setSelectedCells(item.cells)
        self.selector.setSelectedReference(item.reference)
        # Open a dialog
        # message = QMessageBox.information(self, item.name, json.dumps(item.settings.asDict(), indent=4))
        d = QDialog(self, (QtCore.Qt.WindowTitleHint | QtCore.Qt.Window))
        d.setModal(True)
        d.setWindowTitle(item.name)
        l = QGridLayout()
        settingsFrame = SettingsFrame(self.erManager)
        settingsFrame.loadFromSettings(item.settings)
        settingsFrame.loadCameraCorrection(item.cameraCorrection)
        settingsFrame._analysisNameEdit.setText(item.name)
        settingsFrame._analysisNameEdit.setEnabled(False) # Don't allow changing the name.

        okButton = QPushButton("OK")
        okButton.released.connect(d.accept)

        l.addWidget(settingsFrame, 0, 0, 1, 1)
        l.addWidget(okButton, 1, 0, 1, 1)
        d.setLayout(l)
        d.show()
        d.exec()
        item.settings = settingsFrame.getSettings()
        item.cameraCorrection = settingsFrame.getCameraCorrection()

