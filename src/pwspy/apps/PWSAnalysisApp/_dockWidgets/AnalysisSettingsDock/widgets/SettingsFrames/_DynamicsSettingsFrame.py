from __future__ import annotations

from typing import Optional

from PyQt5 import QtCore
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QScrollArea, QGridLayout, QLineEdit, QLabel

from pwspy.analysis.dynamics._analysisSettings import DynamicsAnalysisSettings
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._AbstractSettingsFrame import AbstractSettingsFrame
import typing

from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._sharedWidgets import ExtraReflectanceSelector, \
    VerticallyCompressedWidget, HardwareCorrections
from pwspy.dataTypes import CameraCorrection

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager


class DynamicsSettingsFrame(QScrollArea, AbstractSettingsFrame):
    def __init__(self, erManager: ERManager):
        super().__init__()

        self._frame = VerticallyCompressedWidget(self)
        self._layout = QGridLayout()
        self._frame.setLayout(self._layout)
        self._frame.setFixedWidth(350)
        self.setMinimumWidth(self._frame.width()+5)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setWidget(self._frame)

        row = 0
        self._analysisNameEdit = QLineEdit()
        self._layout.addWidget(QLabel("Analysis Name: "), row, 0, 1, 1)
        self._layout.addWidget(self._analysisNameEdit, row, 1, 1, 1)
        row += 1

        self.hardwareCorrections = HardwareCorrections(self)
        self.hardwareCorrections.stateChanged.connect(self._updateSize)
        self._layout.addWidget(self.hardwareCorrections, row, 0, 1, 4)
        row += 1

        self.extraReflection = ExtraReflectanceSelector(self, erManager)
        self._layout.addWidget(self.extraReflection, row, 0, 1, 4)

        self._updateSize()

    def _updateSize(self):
        height = 100  # give this much excess room.
        height += self.hardwareCorrections.height()
        height += self.extraReflection.height()
        self._frame.setFixedHeight(height)

    @property
    def analysisName(self) -> str:
        return self._analysisNameEdit.text()

    def loadFromSettings(self, settings: DynamicsAnalysisSettings):
        self.extraReflection.loadFromSettings(settings.numericalAperture, settings.referenceMaterial, settings.extraReflectanceId)

    def loadCameraCorrection(self, camCorr: Optional[CameraCorrection] = None):
        self.hardwareCorrections.loadCameraCorrection(camCorr)

    def getSettings(self) -> DynamicsAnalysisSettings:
        erId, refMaterial, numericalAperture = self.extraReflection.getSettings()
        return DynamicsAnalysisSettings(extraReflectanceId=erId,
                                referenceMaterial=refMaterial,
                                numericalAperture=numericalAperture)

    def getCameraCorrection(self) -> CameraCorrection:
        return self.hardwareCorrections.getCameraCorrection()