from __future__ import annotations
from typing import Tuple, List
from PyQt5.QtWidgets import QDockWidget, QWidget, \
    QVBoxLayout, QPushButton, QMessageBox, QTabWidget

from pwspy.analysis import AbstractRuntimeAnalysisSettings
from pwspy.dataTypes import CameraCorrection, AcqDir
from .widgets.QueueAnalysesFrame import AnalysisListItem, QueuedAnalysesFrame
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._PWSSettingsFrame import PWSSettingsFrame

import typing

from .widgets.SettingsFrames import _DynamicsSettingsFrame, DynamicsSettingsFrame
from .widgets.SettingsFrames._AbstractSettingsFrame import AbstractSettingsFrame

if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp._dockWidgets import CellSelectorDock


class AnalysisSettingsDock(QDockWidget):
    def __init__(self, cellSelector: CellSelectorDock, erManager):
        super().__init__("Settings")
        self.erManager = erManager
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.selector = cellSelector
        self.setObjectName('AnalysisSettingsDock')  # needed for restore state to work
        widg = QWidget()
        widg.setLayout(QVBoxLayout())
        self.settingsTabWidget = QTabWidget(self)
        self.PWSSettingsFrame = PWSSettingsFrame(self.erManager, cellSelector)
        self.settingsTabWidget.addTab(self.PWSSettingsFrame, "PWS")
        self.DynSettingsFrame = DynamicsSettingsFrame(self.erManager, cellSelector)
        self.settingsTabWidget.addTab(self.DynSettingsFrame, "Dynamics")
        widg.layout().addWidget(self.settingsTabWidget)
        self.addAnalysisButton = QPushButton("Add Analysis")
        widg.layout().addWidget(self.addAnalysisButton)

        self.analysesQueue = QueuedAnalysesFrame(self)

        widg.layout().addWidget(self.analysesQueue)
        self.analysesQueue.setFixedHeight(50)
        widg.setMinimumHeight(200)
        widg.setMinimumWidth(self.PWSSettingsFrame.minimumWidth() + 10)

        self.addAnalysisButton.released.connect(self.addAnalysis)
        self.setWidget(widg)

    def addAnalysis(self):
        settingsWidget: AbstractSettingsFrame = self.settingsTabWidget.currentWidget()
        try:
            settings = settingsWidget.getSettings()
        except Exception as e:
            QMessageBox.information(self, 'Hold on', str(e))
            return
        self.analysesQueue.addAnalysis(settings)

    def getListedAnalyses(self) -> List[AbstractRuntimeAnalysisSettings]:
        return self.analysesQueue.analyses

