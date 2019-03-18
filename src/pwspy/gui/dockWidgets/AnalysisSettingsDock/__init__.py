from typing import Tuple

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, \
    QVBoxLayout, QPushButton, QSplitter

from pwspy import CameraCorrection
from pwspy.analysis import AnalysisSettings
from pwspy.gui.dockWidgets import CellSelectorDock
from .widgets.QueueAnalysesFrame import AnalysisListItem, QueuedAnalysesFrame
from .widgets.SettingsFrame import SettingsFrame


class AnalysisSettingsDock(QDockWidget):
    def __init__(self, cellSelector: CellSelectorDock):
        super().__init__("Settings")
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.selector = cellSelector
        self.setObjectName('AnalysisSettingsDock')  # needed for restore state to work
        splitter = QSplitter(QtCore.Qt.Vertical, self)
        widg = QWidget()
        widg.setLayout(QVBoxLayout())
        self.settingsFrame = SettingsFrame()
        widg.layout().addWidget(self.settingsFrame)
        self.addAnalysisButton = QPushButton("Add Analysis")
        widg.layout().addWidget(self.addAnalysisButton)
        widg2 = QWidget()
        widg2.setLayout(QVBoxLayout())
        self.analysesQueue = QueuedAnalysesFrame()
        widg2.layout().addWidget(self.analysesQueue)

        self.addAnalysisButton.released.connect(
            lambda: self.analysesQueue.addAnalysis(*self.settingsFrame.getSettings(),
                                                   self.selector.getSelectedReferenceMeta(),
                                                   self.selector.getSelectedCellMetas()))
        #self.analysesQueue.listWidget.currentItemChanged.connect(#TODO Highlight cells and ref)

        splitter.addWidget(widg)
        splitter.addWidget(widg2)
        splitter.setChildrenCollapsible(False)
        self.setWidget(splitter)

    def loadFromSettings(self, settings: AnalysisSettings):
        self.settingsFrame.loadFromSettings(settings)

    def getSettings(self) -> Tuple[CameraCorrection, AnalysisSettings]:
        return self.settingsFrame.getSettings()

    def getAnalysisName(self):
        return self.settingsFrame.analysisName
