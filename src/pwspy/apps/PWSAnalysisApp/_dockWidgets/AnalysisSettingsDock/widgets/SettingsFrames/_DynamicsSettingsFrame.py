from __future__ import annotations

from typing import Optional, Tuple

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QScrollArea, QGridLayout, QLineEdit, QLabel, QGroupBox, QHBoxLayout, QCheckBox

from pwspy.analysis.dynamics._analysisSettings import DynamicsAnalysisSettings, DynamicsRuntimeAnalysisSettings
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._AbstractSettingsFrame import AbstractSettingsFrame
import typing

from ._sharedWidgets import ExtraReflectanceSelector, VerticallyCompressedWidget, HardwareCorrections

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
    from pwspy.dataTypes import CameraCorrection, ERMetadata


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
        row += 1

        '''Use relative or absolute units of reflectance'''
        self.scaling = QGroupBox("Scaling")
        self.scaling.setLayout(QHBoxLayout())
        self.scaling.layout().setContentsMargins(2, 2, 2, 5)
        self.relativeUnits = QCheckBox("Use Relative Units", self)
        self.relativeUnits.setToolTip("If checked then reflectance (and therefore all other parameters) will be scaled such that any reflectance matching that\n"
                                      "of the reference image will be 1. If left unchecked then the `Reference Material` will be used to scale reflectance to\n"
                                      "match the actual physical reflectance of the sample.")
        self.scaling.layout().addWidget(self.relativeUnits)
        self._layout.addWidget(self.scaling, row, 0, 1, 4)

        self._updateSize()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        super().showEvent(a0)
        self._updateSize() #For some reason this must be done here and in the __init__ for it to start up properly.

    def _updateSize(self):
        height = 100  # give this much excess room.
        height += self.hardwareCorrections.height()
        height += self.extraReflection.height()
        height += self.scaling.height()
        self._frame.setFixedHeight(height)

    @property
    def analysisName(self) -> str:
        return self._analysisNameEdit.text()

    def loadFromSettings(self, settings: DynamicsAnalysisSettings):
        self.extraReflection.loadFromSettings(settings.numericalAperture, settings.referenceMaterial, settings.extraReflectanceId)
        self.relativeUnits.setCheckState(2 if settings.relativeUnits else 0)

    def loadCameraCorrection(self, camCorr: Optional[CameraCorrection] = None):
        self.hardwareCorrections.loadCameraCorrection(camCorr)

    def getSettings(self) -> DynamicsRuntimeAnalysisSettings:
        erMetadata, refMaterial, numericalAperture = self.extraReflection.getSettings()
        return DynamicsRuntimeAnalysisSettings(settings=DynamicsAnalysisSettings(extraReflectanceId=erMetadata.idTag,
                                                                                referenceMaterial=refMaterial,
                                                                                numericalAperture=numericalAperture,
                                                                                relativeUnits=self.relativeUnits.checkState() != 0),
                                               extraReflectanceMetaData=erMetadata)

    def getCameraCorrection(self) -> CameraCorrection:
        return self.hardwareCorrections.getCameraCorrection()
