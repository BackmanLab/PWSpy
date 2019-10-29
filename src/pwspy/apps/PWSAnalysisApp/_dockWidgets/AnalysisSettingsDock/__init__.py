from __future__ import annotations
import json
from typing import Tuple, List
from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, \
    QVBoxLayout, QPushButton, QSplitter, QMessageBox, QDialog, QGridLayout, QApplication
from pwspy.dataTypes import CameraCorrection, AcqDir, ERMetadata
from pwspy.analysis.pws import AnalysisSettings
from .widgets.QueueAnalysesFrame import AnalysisListItem, QueuedAnalysesFrame
from .widgets.SettingsFrame import SettingsFrame

import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp._dockWidgets import CellSelectorDock
    from pwspy.dataTypes import ICMetaData


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

        self.analysesQueue = QueuedAnalysesFrame(self)

        widg.layout().addWidget(self.analysesQueue)
        self.analysesQueue.setFixedHeight(50)
        widg.setMinimumHeight(200)
        widg.setMinimumWidth(self.settingsFrame.minimumWidth()+10)

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

    def getListedAnalyses(self) -> List[Tuple[str, AnalysisSettings, List[AcqDir], AcqDir, CameraCorrection]]:
        return self.analysesQueue.analyses

