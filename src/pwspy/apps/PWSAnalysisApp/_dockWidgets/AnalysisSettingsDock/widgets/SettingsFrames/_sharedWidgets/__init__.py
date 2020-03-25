from __future__ import annotations
import os
from typing import Optional, Tuple

from PyQt5 import QtGui, QtCore
from PyQt5.QtGui import QPalette, QValidator, QDoubleValidator
from PyQt5.QtWidgets import QGroupBox, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox, QGridLayout, QSpinBox, QDoubleSpinBox, \
    QComboBox, QFrame, QSpacerItem, QSizePolicy, QLayout

from pwspy.apps import resources
from pwspy.apps.PWSAnalysisApp._sharedWidgets import CollapsibleSection
from pwspy.dataTypes import CameraCorrection
from pwspy.dataTypes._metadata import ERMetaData
from pwspy.utility.reflection import reflectanceHelper, Material
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager


class ExtraReflectanceSelector(QGroupBox):
    def __init__(self, parent: QWidget, erManager: ERManager):
        super().__init__("Extra Reflection", parent)
        self.ERExplorer = None # We delay the instantiation of this window because its __init__ triggers some somewhat slow processes that aren't needed if the window is never opened.
        self._erManager = erManager

        self.setToolTip("The fact that some light captured by the camera is scattered off surfaces inside the objective without ever reaching the sample means\n"
                        "that the light intensity captured by the camera is not proportional to the reflectance of the sample. This extra reflectance varies\n"
                        "spatially and spectrally and must be subtracted from our data in order for the analysis to be accurate. Calibration measurements of\n"
                        "the extra reflectance are periodically uploaded to a google drive account which this software can download from. Click the folder icon\n"
                        "to view and download the available calibration data cubes. Make sure to select one for the correct system and a date that is close to\n"
                        "the acquisition date of your data. The `reference material` should be selected to match the material that was imaged in your reference\n"
                        "image cube (usually Water).")
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 1, 5, 5)
        rsubLabel = QLabel("R Subtraction")
        self.RSubtractionNameLabel = QLineEdit('None')
        self.RSubtractionNameLabel.setReadOnly(True)
        self.RSubtractionBrowseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.svg')), '')
        self.RSubtractionBrowseButton.released.connect(self._browseReflection)
        refMatLabel = QLabel("Reference Material")
        self.refMaterialCombo = QHComboBox()
        self.refMaterialCombo.addItems([k.name for k in reflectanceHelper.materialFiles.keys() if k.name != 'Glass'])
        naLabel = QLabel("Numerical Aperture")
        self.numericalAperture = QHDoubleSpinBox()
        self.numericalAperture.setRange(0, 2)
        self.numericalAperture.setSingleStep(0.1)
        self.numericalAperture.setToolTip("The illumination numerical aperture used. This is usually 0.52 on NU systems."
                                          "This is used to accurately calculate the theoretically expected reflectance of "
                                          "the reference material. We also want to check that the ExtraReflection was taken "
                                          "at the same NA.")
        naLabel.setToolTip(self.numericalAperture.toolTip())
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(rsubLabel)
        _(self.RSubtractionNameLabel)
        _(self.RSubtractionBrowseButton)
        layout.addLayout(rLayout)
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(refMatLabel)
        _(self.refMaterialCombo)
        layout.addLayout(rLayout)
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(naLabel)
        _(self.numericalAperture)
        layout.addLayout(rLayout)
        self.setLayout(layout)

    def getSettings(self) -> Tuple[ERMetaData, Material, float]:
        self._initializeERSelector()
        if self.ERExplorer.getSelectedMetadata() is None:
            ans = QMessageBox.question(self, "Uh", "An extra reflectance cube has not been selected. Do you want to ignore this important correction?")
            if ans == QMessageBox.Yes:
                erMd = None
            else:
                raise ValueError("An extra reflectance cube has not been selected.")
        else:
            erMd = self.ERExplorer.getSelectedMetadata()
        self.numericalAperture.clearFocus() #This should prevent an error where the value that is saved doesn't match what is actually typed in when the keyboard is still focused on the spinbox.
        numericalAperture = self.numericalAperture.value()
        refMaterial = Material[self.refMaterialCombo.currentText()]
        return erMd, refMaterial, numericalAperture

    def getSelectedERMetadata(self) -> Optional[ERMetaData]:
        return self.ERExplorer.getSelectedMetadata()

    def loadFromSettings(self, numericalAperture: float, referenceMaterial: Material, extraReflectanceId: str):
        if extraReflectanceId is not None:
            self._initializeERSelector()
            try:
                md = self._erManager.getMetadataFromId(extraReflectanceId)
                self.ERExplorer.setSelection(md)
            except IndexError:  # Metadata matching that ID was not found by the ERManager
                self.RSubtractionNameLabel.setText(f"Failed to find ID: {extraReflectanceId}")
        if referenceMaterial is None:  # Even though choosing a referenceMaterial of None is no longer an option, it was in the past, we still support loading these settings.
            self.refMaterialCombo.setCurrentText("Ignore")
        else:
            self.refMaterialCombo.setCurrentIndex(self.refMaterialCombo.findText(referenceMaterial.name))
        self.numericalAperture.setValue(numericalAperture)

    def _browseReflection(self):
        self._initializeERSelector()
        self.ERExplorer.show()

    def _initializeERSelector(self):
        if self.ERExplorer is None:  # Don't initialize the ERSelector window until we actually need it. It can be slow to initiate
            self.ERExplorer = self._erManager.createSelectorWindow(self)

            def extraReflectionChanged(md: Optional[ERMetaData]):
                if md is None:
                    self.RSubtractionNameLabel.setText('None')
                else:
                    self.RSubtractionNameLabel.setText(os.path.split(md.filePath)[-1])

            self.ERExplorer.selectionChanged.connect(extraReflectionChanged)

class HardwareCorrections(CollapsibleSection):
    def __init__(self, parent: QWidget):
        super().__init__('Automatic Correction', 200, parent)
        layout = QGridLayout()
        dcLabel = QLabel('Dark Counts')
        self.darkCountBox = QHSpinBox()
        self.darkCountBox.setToolTip("The counts/pixel reported by the camera when it is not exposed to any light."
                                     " e.g if using 2x2 binning and you measure 400 counts, then the value to put here is 100.")
        dcLabel.setToolTip(self.darkCountBox.toolTip())
        self.darkCountBox.setRange(0, 10000)
        linLabel = QLabel("Linearity Correction")
        self.linearityEdit = QLineEdit()
        self.linearityEdit.setText("1")
        self.linearityEdit.setToolTip("A comma-separated polynomial to linearize the counts from the camera."
                                      "E.G an entry of A,B,C here will result in the data being transformed as newData = A * data + B * data^2 + C * data^3."
                                      "Leaving this as '1' will result in no transformation (usually CMOS cameras are already linear)")
        linLabel.setToolTip(self.linearityEdit.toolTip())
        self.linearityEdit.setValidator(HardwareCorrections.CsvValidator())
        origPalette = self.linearityEdit.palette()
        palette = QPalette()
        palette.setColor(QPalette.Text, QtCore.Qt.red)
        self.linearityEdit.validator().stateChanged.connect(lambda state:
                                                            self.linearityEdit.setPalette(
                                                                palette) if state != QValidator.Acceptable else self.linearityEdit.setPalette(origPalette))

        _ = layout.addWidget
        _(dcLabel, 0, 0)
        _(self.darkCountBox, 0, 1)
        _(linLabel, 1, 0)
        _(self.linearityEdit, 1, 1)

        self.setToolTip("The relationship between camera counts and light intensity is not always linear."
                                            "The correction parameters can usually be found automatically in the image metadata.")
        self.setLayout(layout)

    def getCameraCorrection(self) -> CameraCorrection:
        if self.checkState() == 0:
            if self.linearityEdit.validator().state != QValidator.Acceptable:
                raise ValueError("The camera linearity correction input is not valid.")
            linText = self.linearityEdit.text()
            linearityPoly = tuple(float(i) for i in linText.split(','))
            cameraCorrection = CameraCorrection(self.darkCountBox.value(), linearityPoly)
        else:
            cameraCorrection = None
        return cameraCorrection

    def loadCameraCorrection(self, camCorr: Optional[CameraCorrection] = None):
        if camCorr is None: #Automatic camera corrections
            self.setCheckState(2)
        else:
            self.setCheckState(0)
            if camCorr.linearityPolynomial is None:
                self.linearityEdit.setText("1")
            else:
                self.linearityEdit.setText(",".join((str(i) for i in camCorr.linearityPolynomial)))
            self.darkCountBox.setValue(camCorr.darkCounts)

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


def humble(clas):
    """Returns a subclass of clas that will not allow scrolling unless it has been actively selected."""
    class HumbleDoubleSpinBox(clas):
        def __init__(self, *args):
            super(HumbleDoubleSpinBox, self).__init__(*args)
            self.setFocusPolicy(QtCore.Qt.StrongFocus)

        def focusInEvent(self, event):
            self.setFocusPolicy(QtCore.Qt.WheelFocus)
            super(HumbleDoubleSpinBox, self).focusInEvent(event)

        def focusOutEvent(self, event):
            self.setFocusPolicy(QtCore.Qt.StrongFocus)
            super(HumbleDoubleSpinBox, self).focusOutEvent(event)

        def wheelEvent(self, event):
            if self.hasFocus():
                return super(HumbleDoubleSpinBox, self).wheelEvent(event)
            else:
                event.ignore()
    return HumbleDoubleSpinBox


QHSpinBox = humble(QSpinBox)
QHDoubleSpinBox = humble(QDoubleSpinBox)
QHComboBox = humble(QComboBox)


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