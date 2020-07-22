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
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QScrollArea, QGridLayout, QLineEdit, QLabel, QGroupBox, QHBoxLayout, QCheckBox, QMessageBox

import pwspy.analysis.dynamics
from pwspy.apps.PWSAnalysisApp._dockWidgets import CellSelectorDock
from pwspy.apps.PWSAnalysisApp.componentInterfaces import CellSelector
from pwspy.utility.reflection import Material
from ._AbstractSettingsFrame import AbstractSettingsFrame

from ._sharedWidgets import ExtraReflectanceSelector, VerticallyCompressedWidget, HardwareCorrections

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager


class DynamicsSettingsFrame(QScrollArea, AbstractSettingsFrame):
    def __init__(self, erManager: ERManager, cellSelector: CellSelector):
        super().__init__()
        self.cellSelector = cellSelector

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
        self.extraReflection.loadFromSettings(0.52, Material.Water, None)
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
        self.relativeUnits.setChecked(True)
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

    def loadFromSettings(self, settings: pwspy.analysis.dynamics.DynamicsAnalysisSettings):
        self.extraReflection.loadFromSettings(settings.numericalAperture, settings.referenceMaterial, settings.extraReflectanceId)
        self.relativeUnits.setCheckState(2 if settings.relativeUnits else 0)
        self.hardwareCorrections.loadCameraCorrection(settings.cameraCorrection)

    def getSettings(self) -> pwspy.analysis.dynamics.DynamicsRuntimeAnalysisSettings:
        erMetadata, refMaterial, numericalAperture = self.extraReflection.getSettings()
        refMeta = self.cellSelector.getSelectedReferenceMeta()
        cellMeta = self.cellSelector.getSelectedCellMetas()
        name = self._analysisNameEdit.text()
        if refMeta is None:
            raise ValueError('Please select a reference Cell.')
        if name == '':
            raise ValueError("Please give your analysis a name.")
        if len(cellMeta) == 0:
            raise ValueError('Please select cells to analyse.')
        refMeta = refMeta.dynamics
        cellMeta = [i.dynamics for i in cellMeta if i.dynamics is not None]  # If we select some acquisitions that don't have dynamics then they'll get stripped out here
        if refMeta is None:
            raise ValueError("The selected reference acquisition has no valid Dynamics data.")
        if len(cellMeta) == 0:
            raise ValueError("No valid Dynamics acquisitions were selected.")
        return pwspy.analysis.dynamics.DynamicsRuntimeAnalysisSettings(settings=pwspy.analysis.dynamics.DynamicsAnalysisSettings(extraReflectanceId=erMetadata.idTag if erMetadata is not None else None,
                                                                                                                                 referenceMaterial=refMaterial,
                                                                                                                                 numericalAperture=numericalAperture,
                                                                                                                                 relativeUnits=self.relativeUnits.checkState() != 0,
                                                                                                                                 cameraCorrection=self.hardwareCorrections.getCameraCorrection()),
                                                                       extraReflectanceMetadata=erMetadata,
                                                                       referenceMetadata=refMeta,
                                                                       cellMetadata=cellMeta,
                                                                       analysisName=name)
