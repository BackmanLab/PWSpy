from __future__ import annotations
import os
from glob import glob
from typing import Optional, Tuple
import typing

from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._AbstractSettingsFrame import AbstractSettingsFrame
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._sharedWidgets import ExtraReflectanceSelector, HardwareCorrections, \
    QHSpinBox, QHDoubleSpinBox, VerticallyCompressedWidget

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QScrollArea, QGridLayout, QLineEdit, QLabel, QGroupBox, QHBoxLayout, QWidget, QRadioButton, \
    QFrame, QCheckBox

from pwspy.dataTypes import CameraCorrection
from pwspy.dataTypes.metadata import ERMetaData
from pwspy.analysis.pws import PWSAnalysisSettings, PWSRuntimeAnalysisSettings
from pwspy.apps.PWSAnalysisApp import applicationVars
from pwspy.apps.PWSAnalysisApp._sharedWidgets.collapsibleSection import CollapsibleSection


class PWSSettingsFrame(AbstractSettingsFrame, QScrollArea):
    def __init__(self, erManager: ERManager):
        super().__init__()

        self._frame = VerticallyCompressedWidget(self)
        self._layout = QGridLayout()
        self._frame.setLayout(self._layout)
        self._frame.setFixedWidth(350)
        self.setMinimumWidth(self._frame.width()+5)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setWidget(self._frame)

        """Set up Frame"""
        """Presets"""
        row = 0
        self._analysisNameEdit = QLineEdit()
        self._layout.addWidget(QLabel("Analysis Name: "), row, 0, 1, 1)
        self._layout.addWidget(self._analysisNameEdit, row, 1, 1, 1)
        row += 1
        self.presets = QGroupBox("Presets")
        self.presets.setLayout(QHBoxLayout())
        self.presets.layout().setContentsMargins(0, 0, 0, 5)
        _2 = QWidget()
        _2.setLayout(QHBoxLayout())
        _2.layout().setContentsMargins(5, 0, 5, 0)
        for f in glob(os.path.join(applicationVars.analysisSettingsDirectory, '*_analysis.json')):
            name = os.path.split(f)[-1][:-14]
            b = QRadioButton(name)
            b.released.connect(
                lambda n=name: self.loadFromSettings(
                    PWSAnalysisSettings.fromJson(applicationVars.analysisSettingsDirectory, n)))
            _2.layout().addWidget(b)
        _ = QScrollArea()
        _.setWidget(_2)
        _.setFrameShape(QFrame.NoFrame)
        _.setContentsMargins(0, 0, 0, 0)
        _.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        _.horizontalScrollBar().setStyleSheet("QScrollBar:horizontal { height: 10px; }")
        self.presets.setFixedHeight(45)
        self.presets.layout().addWidget(_)
        self._layout.addWidget(self.presets, row, 0, 1, 4)
        row += 1

        '''Hardwarecorrections'''
        self.hardwareCorrections = HardwareCorrections(self)
        self.hardwareCorrections.stateChanged.connect(self._updateSize)
        self._layout.addWidget(self.hardwareCorrections, row, 0, 1, 4)
        row += 1

        '''Extra Reflection'''
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
        row += 1

        '''SignalPreparations'''
        self.signalPrep = QGroupBox("Signal Prep")
        self.signalPrep.setFixedSize(175, 75)
        self.signalPrep.setToolTip("In order to reduce the effects of measurement noise we filter out the high frequencies from our signal. We do this using a\n"
                                   "Buttersworth low-pass filter. Best to stick with the defaults on this one.")
        layout = QGridLayout()
        layout.setContentsMargins(5, 1, 5, 5)
        _ = layout.addWidget
        orderLabel = QLabel("Filter Order")
        self.filterOrder = QHSpinBox()
        self.filterOrder.setRange(0, 6)
        self.filterOrder.setToolTip("A lowpass filter is applied to the spectral signal to reduce noise. This determines the `order` of the digital filter.")
        orderLabel.setToolTip(self.filterOrder.toolTip())
        cutoffLabel = QLabel("Cutoff Freq.")
        self.filterCutoff = QHDoubleSpinBox()
        self.filterCutoff.setToolTip("The frequency in units of 1/wavelength for the filter cutoff.")
        cutoffLabel.setToolTip(self.filterCutoff.toolTip())
        _(orderLabel, 0, 0, 1, 1)
        _(self.filterOrder, 0, 1, 1, 1)
        _(cutoffLabel, 1, 0, 1, 1)
        _(self.filterCutoff, 1, 1, 1, 1)
        _(QLabel("nm<sup>-1</sup>"), 1, 2, 1, 1)
        self.signalPrep.setLayout(layout)
        self._layout.addWidget(self.signalPrep, row, 0, 1, 2)

        '''Cropping'''
        self.cropping = QGroupBox("Wavelength Cropping")
        self.cropping.setFixedSize(125, 75)
        self.cropping.setToolTip("In the past it was found that there was exceptionally high noise at the very beginning and end of an acquisition. For this reason we would exclude the first and last wavelengths of the image cube. While it is likely that the noise issue has now been fixed we still do this for consistency's sake.")
        layout = QGridLayout()
        layout.setContentsMargins(5, 1, 5, 5)
        _ = layout.addWidget
        self.wavelengthStart = QHSpinBox()
        self.wavelengthStop = QHSpinBox()
        self.wavelengthStart.setToolTip("Sometimes the beginning and end of the spectrum can have very high noise. For this reason we crop the data before analysis.")
        self.wavelengthStop.setToolTip("Sometimes the beginning and end of the spectrum can have very high noise. For this reason we crop the data before analysis.")
        self.wavelengthStart.setRange(300, 800)
        self.wavelengthStop.setRange(300, 800)
        _(QLabel("Start"), 0, 0)
        _(QLabel("Stop"), 0, 1)
        _(self.wavelengthStart, 1, 0)
        _(self.wavelengthStop, 1, 1)
        self.cropping.setLayout(layout)
        self._layout.addWidget(self.cropping, row, 2, 1, 2)
        row += 1

        '''Polynomial subtraction'''
        self.polySub = QGroupBox("Polynomial Subtraction")
        self.polySub.setFixedSize(150, 50)
        self.polySub.setToolTip("A polynomial is fit to each spectrum and then it is subtracted from the spectrum."
                                        "This is so that we remove effects of absorbtion and our final signal is only due to interference")
        layout = QGridLayout()
        layout.setContentsMargins(5, 1, 5, 5)
        _ = layout.addWidget
        self.polynomialOrder = QHSpinBox()
        _(QLabel("Order"), 0, 0, 1, 1)
        _(self.polynomialOrder, 0, 1, 1, 1)
        self.polySub.setLayout(layout)
        self._layout.addWidget(self.polySub, row, 0, 1, 2)
        row += 1

        '''Advanced Calculations'''
        self.advanced = CollapsibleSection('Skip Advanced Analysis', 200, self)
        self.advanced.stateChanged.connect(self._updateSize)
        self.advanced.setToolTip("If this box is ticked then some of the less common analyses will be skipped. This saves time and harddrive space.")
        self.autoCorrStopIndex = QHSpinBox()
        self.autoCorrStopIndex.setToolTip("Autocorrelation slope is determined by fitting a line to the first values of the autocorrelation function. This value determines how many values to include in this linear fit.")
        self.minSubCheckBox = QCheckBox("MinSub")
        self.minSubCheckBox.setToolTip("The calculation of autocorrelation decay slope involves taking the natural logarithm of of the autocorrelation. However noise often causes the autocorrelation to have negative values which causes problems for the logarithm. Checking this box adds an offset to the autocorrelation so that no values are negative.")
        layout = QGridLayout()
        _ = layout.addWidget
        _(QLabel("AutoCorr Stop Index"), 0, 0, 1, 1)
        _(self.autoCorrStopIndex, 0, 1, 1, 1)
        _(self.minSubCheckBox, 1, 0, 1, 1)
        self.advanced.setLayout(layout)
        self._layout.addWidget(self.advanced, row, 0, 1, 4)
        row += 1

        self._updateSize()

    def showEvent(self, a0: QtGui.QShowEvent) -> None:
        super().showEvent(a0)
        self._updateSize() #For some reason this must be done here and in the __init__ for it to start up properly.

    @property
    def analysisName(self) -> str:
        return self._analysisNameEdit.text()

    def _updateSize(self):
        height = 100  # give this much excess room.
        height += self.presets.height()
        height += self.hardwareCorrections.height()
        height += self.extraReflection.height()
        height += self.scaling.height()
        height += self.signalPrep.height()
        height += self.polySub.height()
        height += self.advanced.height()
        self._frame.setFixedHeight(height)

    def loadFromSettings(self, settings: PWSAnalysisSettings):
        self.filterOrder.setValue(settings.filterOrder)
        self.filterCutoff.setValue(settings.filterCutoff)
        self.polynomialOrder.setValue(settings.polynomialOrder)
        self.extraReflection.loadFromSettings(settings.numericalAperture, settings.referenceMaterial, settings.extraReflectanceId)
        self.wavelengthStop.setValue(settings.wavelengthStop)
        self.wavelengthStart.setValue(settings.wavelengthStart)
        self.advanced.setCheckState(2 if settings.skipAdvanced else 0)
        self.autoCorrStopIndex.setValue(settings.autoCorrStopIndex)
        self.minSubCheckBox.setCheckState(2 if settings.autoCorrMinSub else 0)
        self.relativeUnits.setCheckState(2 if settings.relativeUnits else 0)

    def loadCameraCorrection(self, camCorr: Optional[CameraCorrection] = None):
        self.hardwareCorrections.loadCameraCorrection(camCorr)

    def getSettings(self) -> PWSRuntimeAnalysisSettings:
        erMetadata, refMaterial, numericalAperture = self.extraReflection.getSettings()
        return PWSRuntimeAnalysisSettings(settings=PWSAnalysisSettings(filterOrder=self.filterOrder.value(),  # TODO include reference and camera correction with this object.
                                                                       filterCutoff=self.filterCutoff.value(),
                                                                       polynomialOrder=self.polynomialOrder.value(),
                                                                       extraReflectanceId=erMetadata.idTag if erMetadata is not None else None,
                                                                       referenceMaterial=refMaterial,
                                                                       wavelengthStart=self.wavelengthStart.value(),
                                                                       wavelengthStop=self.wavelengthStop.value(),
                                                                       skipAdvanced=self.advanced.checkState() != 0,
                                                                       autoCorrMinSub=self.minSubCheckBox.checkState() != 0,
                                                                       autoCorrStopIndex=self.autoCorrStopIndex.value(),
                                                                       numericalAperture=numericalAperture,
                                                                       relativeUnits=self.relativeUnits.checkState() != 0),
                                          extraReflectanceMetadata=erMetadata)

    def getCameraCorrection(self) -> CameraCorrection:
        return self.hardwareCorrections.getCameraCorrection()



