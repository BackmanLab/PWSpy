# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations
import typing
from PyQt5.QtWidgets import QDockWidget, QWidget, \
    QVBoxLayout, QPushButton, QMessageBox, QTabWidget

from pwspy.analysis import AbstractRuntimeAnalysisSettings
from .widgets.QueueAnalysesFrame import AnalysisListItem, QueuedAnalysesFrame
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames import PWSSettingsFrame
from .widgets.SettingsFrames import DynamicsSettingsFrame
from .widgets.SettingsFrames import AbstractSettingsFrame
from pwspy.apps.PWSAnalysisApp.componentInterfaces import CellSelector, AnalysisSettingsCreator


class AnalysisSettingsDock(AnalysisSettingsCreator, QDockWidget):
    def __init__(self, cellSelector: CellSelector, erManager):
        super().__init__("Settings")
        self._erManager = erManager
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self._selector = cellSelector
        self.setObjectName('AnalysisSettingsDock')  # needed for restore state to work
        widg = QWidget()
        widg.setLayout(QVBoxLayout())
        self._settingsTabWidget = QTabWidget(self)
        self._PWSSettingsFrame = PWSSettingsFrame(self._erManager, cellSelector)
        self._settingsTabWidget.addTab(self._PWSSettingsFrame, "PWS")
        self._DynSettingsFrame = DynamicsSettingsFrame(self._erManager, cellSelector)
        self._settingsTabWidget.addTab(self._DynSettingsFrame, "Dynamics")
        widg.layout().addWidget(self._settingsTabWidget)
        self.addAnalysisButton = QPushButton("Add Analysis")
        widg.layout().addWidget(self.addAnalysisButton)

        self._analysesQueue = QueuedAnalysesFrame(self)

        widg.layout().addWidget(self._analysesQueue)
        self._analysesQueue.setFixedHeight(50)
        widg.setMinimumHeight(200)
        widg.setMinimumWidth(self._PWSSettingsFrame.minimumWidth() + 10)

        self.addAnalysisButton.released.connect(self._addAnalysis)
        self.setWidget(widg)

    def _addAnalysis(self):
        settingsWidget: AbstractSettingsFrame = self._settingsTabWidget.currentWidget()
        try:
            settings = settingsWidget.getSettings()
        except Exception as e:
            QMessageBox.information(self, 'Hold on', str(e))
            return
        self._analysesQueue.addAnalysis(settings)

    def getListedAnalyses(self) -> typing.List[AbstractRuntimeAnalysisSettings]:
        return self._analysesQueue.analyses

