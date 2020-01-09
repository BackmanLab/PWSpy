from __future__ import annotations

from PyQt5.QtWidgets import QScrollArea, QGridLayout, QLineEdit, QLabel

from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._AbstractSettingsFrame import AbstractSettingsFrame
import typing

from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._sharedWidgets import ExtraReflectanceSelector

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager


class DynamicsSettingsFrame(QScrollArea):#(AbstractSettingsFrame):
    def __init__(self, erManager: ERManager):
        super().__init__()
        layout = QGridLayout(self)
        row = 0
        self._analysisNameEdit = QLineEdit()
        layout.addWidget(QLabel("Analysis Name: "), row, 0, 1, 1)
        layout.addWidget(self._analysisNameEdit, row, 1, 1, 1)
        row += 1

        self.extraReflection = ExtraReflectanceSelector(self, erManager)
        layout.addWidget(self.extraReflection, row, 0, 1, 4)

        self.setLayout(layout)