from __future__ import annotations
import os
from glob import glob
from typing import Optional
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager.manager import ERManager

from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPalette, QValidator, QDoubleValidator
from PyQt5.QtWidgets import QScrollArea, QGridLayout, QLineEdit, QLabel, QGroupBox, QHBoxLayout, QWidget, QRadioButton, \
    QFrame, QSpinBox, QVBoxLayout, QPushButton, QComboBox, QDoubleSpinBox, QCheckBox, QMessageBox, QSpacerItem, QSizePolicy, QLayout

from pwspy.dataTypes import CameraCorrection
from pwspy.analysis import AnalysisSettings
from pwspy.apps.PWSAnalysisApp import applicationVars
from pwspy.apps import resources
from pwspy.apps.PWSAnalysisApp._sharedWidgets.collapsibleSection import CollapsibleSection
from pwspy.utility.reflection import reflectanceHelper
from pwspy.moduleConsts import Material


class SettingsFrame(QScrollArea):
    def __init__(self, erManager: ERManager):
        super().__init__()
        self.ERExplorer = erManager.createSelectorWindow(self)
        self.ERExplorer.selectionChanged.connect(lambda md: self.RSubtractionNameLabel.setText(os.path.split(md.filePath)[-1]))
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
                AnalysisSettings.fromJson(applicationVars.analysisSettingsDirectory, n)))
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
        layout = QGridLayout()
        self.darkCountBox = QSpinBox()
        self.darkCountBox.setToolTip("The counts/pixel reported by the camera when it is not exposed to any light."
                                     " e.g if using 2x2 binning and you measure 400 counts, then the value to put here is 100.")
        self.darkCountBox.setRange(0, 10000)
        self.linearityEdit = QLineEdit()
        self.linearityEdit.setText("1")
        self.linearityEdit.setToolTip("A comma-separated polynomial to linearize the counts from the camera."
                                        "E.G an entry of A,B,C here will result in the data being transformed as newData = A * data + B * data^2 + C * data^3."
                                      "Leaving this as '1' will result in no transformation (usually CMOS cameras are already linear)")
        self.linearityEdit.setValidator(CsvValidator())
        origPalette = self.linearityEdit.palette()
        palette = QPalette()
        palette.setColor(QPalette.Text, QtCore.Qt.red)
        self.linearityEdit.validator().stateChanged.connect(lambda state:
            self.linearityEdit.setPalette(palette) if state != QValidator.Acceptable else self.linearityEdit.setPalette(origPalette))

        _ = layout.addWidget
        _(QLabel('Dark Counts'), 0, 0)
        _(self.darkCountBox, 0, 1)
        _(QLabel("Linearity Correction"), 1, 0)
        _(self.linearityEdit, 1, 1)
        self.hardwareCorrections = CollapsibleSection('Automatic Correction', 200, self)
        self.hardwareCorrections.stateChanged.connect(self._updateSize)
        self.hardwareCorrections.setToolTip("The relationship between camera counts and light intensity is not always linear."
                                            "The correction parameters can usually be found automatically in the image metadata.")
        self.hardwareCorrections.setLayout(layout)
        self._layout.addWidget(self.hardwareCorrections, row, 0, 1, 4)
        row += 1

        '''Extra Reflection'''
        self.extraReflection = QGroupBox("Extra Reflection")
        self.extraReflection.setToolTip("The fact that some light captured by the camera is scattered off surfaces inside the objective without ever reaching the sample means that the light intensity captured by the camera is not proportional to the reflectance of the sample. This extra reflectance varies spatially and spectrally and must be subtracted from our data in order for the analysis to be accurate. Calibration measurements of the extra reflectance are periodically uploaded to a google drive account which this software can download from. Click the folder icon to view and download the available calibration data cubes. Make sure to select one for the correct system and a date that is close to the acquisition date of your data. The `reference material` should be selected to match the material that was imaged in your reference image cube (usually Water).")
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 1, 5, 5)
        self.RSubtractionNameLabel = QLineEdit()
        self.RSubtractionNameLabel.setEnabled(False)
        self.RSubtractionBrowseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.svg')), '')
        self.RSubtractionBrowseButton.released.connect(self._browseReflection)
        self.refMaterialCombo = QComboBox()
        self.refMaterialCombo.addItems([k.name for k in reflectanceHelper.materialFiles.keys() if k.name != 'Glass'])
        self.refMaterialCombo.addItem("Ignore")
        self.numericalAperture = QDoubleSpinBox()
        self.numericalAperture.setRange(0, 2)
        self.numericalAperture.setToolTip("The illumination numerical aperture used. This is usually 0.52 on NU systems."
                                          "This is used to accurately calculate the theoretically expected reflectance of "
                                          "the reference material. We also want to check that the ExtraReflection was taken "
                                          "at the same NA.")
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(QLabel("R Subtraction"))
        _(self.RSubtractionNameLabel)
        _(self.RSubtractionBrowseButton)
        layout.addLayout(rLayout)
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(QLabel("Reference Material"))
        _(self.refMaterialCombo)
        layout.addLayout(rLayout)
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(QLabel("Numerical Aperture"))
        _(self.numericalAperture)
        layout.addLayout(rLayout)
        self.extraReflection.setLayout(layout)
        self._layout.addWidget(self.extraReflection, row, 0, 1, 4)
        row += 1

        '''SignalPreparations'''
        self.signalPrep = QGroupBox("Signal Prep")
        self.signalPrep.setFixedSize(175, 75)
        self.signalPrep.setToolTip("In order to reduce the effects of measurement noise we filter out the high frequencies from our signal. We do this using a Buttersworth low-pass filter. Best to stick with the defaults on this one.")
        layout = QGridLayout()
        layout.setContentsMargins(5, 1, 5, 5)
        _ = layout.addWidget
        self.filterOrder = QSpinBox()
        self.filterOrder.setRange(0, 6)
        self.filterOrder.setToolTip("A lowpass filter is applied to the spectral signal to reduce noise. This determines the `order` of the digital filter.")
        self.filterCutoff = QDoubleSpinBox()
        self.filterCutoff.setToolTip("The frequency in units of 1/wavelength for the filter cutoff.")
        _(QLabel("Filter Order"), 0, 0, 1, 1)
        _(self.filterOrder, 0, 1, 1, 1)
        _(QLabel("Cutoff Freq."), 1, 0, 1, 1)
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
        self.wavelengthStart = QSpinBox()
        self.wavelengthStop = QSpinBox()
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
        self.polynomialOrder = QSpinBox()
        _(QLabel("Order"), 0, 0, 1, 1)
        _(self.polynomialOrder, 0, 1, 1, 1)
        self.polySub.setLayout(layout)
        self._layout.addWidget(self.polySub, row, 0, 1, 2)
        row += 1

        '''Advanced Calculations'''
        self.advanced = CollapsibleSection('Skip Advanced Analysis', 200, self)
        self.advanced.stateChanged.connect(self._updateSize)
        self.advanced.setToolTip("If this box is ticked then some of the less common analyses will be skipped. This saves time and harddrive space.")
        self.autoCorrStopIndex = QSpinBox()
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
        height += self.signalPrep.height()
        height += self.polySub.height()
        height += self.advanced.height()
        self._frame.setFixedHeight(height)

    # noinspection PyTypeChecker
    def loadFromSettings(self, settings: AnalysisSettings):
        self.filterOrder.setValue(settings.filterOrder)
        self.filterCutoff.setValue(settings.filterCutoff)
        self.polynomialOrder.setValue(settings.polynomialOrder)
        if settings.extraReflectanceId is not None:
            self.ERExplorer.setSelection(settings.extraReflectanceId)
        if settings.referenceMaterial is None:
            self.refMaterialCombo.setCurrentText("Ignore")
        else:
            self.refMaterialCombo.setCurrentIndex(self.refMaterialCombo.findText(settings.referenceMaterial.name))
        self.wavelengthStop.setValue(settings.wavelengthStop)
        self.wavelengthStart.setValue(settings.wavelengthStart)
        self.advanced.setCheckState(2 if settings.skipAdvanced else 0)
        self.autoCorrStopIndex.setValue(settings.autoCorrStopIndex)
        self.minSubCheckBox.setCheckState(2 if settings.autoCorrMinSub else 0)
        self.numericalAperture.setValue(settings.numericalAperture)

    def loadCameraCorrection(self, camCorr: Optional[CameraCorrection] = None):
        if camCorr is None: #Automatic camera corrections
            self.hardwareCorrections.setCheckState(2)
        else:
            self.hardwareCorrections.setCheckState(0)
            if camCorr.linearityPolynomial is None:
                self.linearityEdit.setText("1")
            else:
                self.linearityEdit.setText(",".join((str(i) for i in camCorr.linearityPolynomial)))
            self.darkCountBox.setValue(camCorr.darkCounts)

    def getSettings(self) -> AnalysisSettings:
        if self.ERExplorer.getSelectedId() is None:
            ans = QMessageBox.question(self, "Uh", "An extra reflectance cube has not been selected. Do you want to ignore this important correction?")
            if ans == QMessageBox.Yes:
                erId = None
            else:
                raise ValueError("An extra reflectance cube has not been selected.")
        else:
            erId = self.ERExplorer.getSelectedId()
        refMaterial = None if self.refMaterialCombo.currentText() == "Ignore" else Material[self.refMaterialCombo.currentText()]
        return AnalysisSettings(filterOrder=self.filterOrder.value(),
                                 filterCutoff=self.filterCutoff.value(),
                                 polynomialOrder=self.polynomialOrder.value(),
                                 extraReflectanceId=erId,
                                 referenceMaterial=refMaterial,
                                 wavelengthStart=self.wavelengthStart.value(),
                                 wavelengthStop=self.wavelengthStop.value(),
                                 skipAdvanced=self.advanced.checkState() != 0,
                                 autoCorrMinSub=self.minSubCheckBox.checkState() != 0,
                                 autoCorrStopIndex=self.autoCorrStopIndex.value(),
                                 numericalAperture=self.numericalAperture.value())

    def getCameraCorrection(self) -> CameraCorrection:
        if self.hardwareCorrections.checkState() == 0:
            if self.linearityEdit.validator().state != QValidator.Acceptable:
                raise ValueError("The camera linearity correction input is not valid.")
            linText = self.linearityEdit.text()
            linearityPoly = tuple(float(i) for i in linText.split(','))
            cameraCorrection = CameraCorrection(self.darkCountBox.value(), linearityPoly)
        else:
            cameraCorrection = None
        return cameraCorrection

    def _browseReflection(self):
        self.ERExplorer.show()


class CsvValidator(QValidator):
    stateChanged = QtCore.pyqtSignal(QValidator.State)

    def __init__(self):
        super().__init__()
        self.doubleValidator = QDoubleValidator()
        self.state = QValidator.Acceptable

    def validate(self, inp: str, pos: int):
        oldState = self.state
        for i in inp.split(','):
            ret = self.doubleValidator.validate(i, pos)
            if ret[0] == QValidator.Intermediate:
                self.state = ret[0]
                if self.state != oldState: self.stateChanged.emit(self.state)
                return self.state, inp, pos
            elif ret[0] == QValidator.Invalid:
                return ret
        self.state = QValidator.Acceptable
        if self.state != oldState: self.stateChanged.emit(self.state)
        return self.state, inp, pos


class VerticallyCompressedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        self._contentsFrame = QFrame()
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout().addWidget(self._contentsFrame)
        self.layout().addItem(spacer)
        self.layout = self._layout # override methods
        self.setLayout = self._setLayout

    def _layout(self) -> QLayout:
        return self._contentsFrame.layout()

    def _setLayout(self, layout: QLayout):
        self._contentsFrame.setLayout(layout)