import os
from typing import Optional

from PyQt5 import QtGui
from PyQt5.QtWidgets import QGroupBox, QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox

from pwspy.apps import resources
from pwspy.apps.PWSAnalysisApp._dockWidgets.AnalysisSettingsDock.widgets.SettingsFrames._PWSSettingsFrame import QHComboBox, QHDoubleSpinBox
from pwspy.dataTypes import ERMetadata
from pwspy.moduleConsts import Material
from pwspy.utility.reflection import reflectanceHelper


class ExtraReflectanceSelector(QGroupBox):
    def __init__(self, parent: QWidget, erManager: ERManager):
        super().__init__("Extra Reflection", parent)
        self.ERExplorer = erManager.createSelectorWindow(self)

        def extraReflectionChanged(md: Optional[ERMetadata]):
            if md is None:
                self.RSubtractionNameLabel.setText('None')
            else:
                self.RSubtractionNameLabel.setText(os.path.split(md.filePath)[-1])

        self.ERExplorer.selectionChanged.connect(extraReflectionChanged)

        self.setToolTip("The fact that some light captured by the camera is scattered off surfaces inside the objective without ever reaching the sample means that the light intensity captured by the camera is not proportional to the reflectance of the sample. This extra reflectance varies spatially and spectrally and must be subtracted from our data in order for the analysis to be accurate. Calibration measurements of the extra reflectance are periodically uploaded to a google drive account which this software can download from. Click the folder icon to view and download the available calibration data cubes. Make sure to select one for the correct system and a date that is close to the acquisition date of your data. The `reference material` should be selected to match the material that was imaged in your reference image cube (usually Water).")
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 1, 5, 5)
        rsubLabel = QLabel("R Subtraction")
        self.RSubtractionNameLabel = QLineEdit('None')
        self.RSubtractionNameLabel.setEnabled(False)
        self.RSubtractionBrowseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.svg')), '')
        self.RSubtractionBrowseButton.released.connect(self._browseReflection)
        refMatLabel = QLabel("Reference Material")
        self.refMaterialCombo = QHComboBox()
        self.refMaterialCombo.addItems([k.name for k in reflectanceHelper.materialFiles.keys() if k.name != 'Glass'])
        self.refMaterialCombo.addItem("Ignore")
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

    def getSettings(self):
        if self.ERExplorer.getSelectedId() is None:
            ans = QMessageBox.question(self, "Uh", "An extra reflectance cube has not been selected. Do you want to ignore this important correction?")
            if ans == QMessageBox.Yes:
                erId = None
            else:
                raise ValueError("An extra reflectance cube has not been selected.")
        else:
            erId = self.ERExplorer.getSelectedId()
        numericalAperture = self.numericalAperture.value()
        refMaterial = None if self.refMaterialCombo.currentText() == "Ignore" else Material[self.refMaterialCombo.currentText()]
        return erId, refMaterial, numericalAperture

    def loadFromSettings(self, numericalAperture: float, referenceMaterial: Material, extraReflectanceId: str):
        if extraReflectanceId is not None:
            self.ERExplorer.setSelection(extraReflectanceId)
        if referenceMaterial is None:
            self.refMaterialCombo.setCurrentText("Ignore")
        else:
            self.refMaterialCombo.setCurrentIndex(self.refMaterialCombo.findText(referenceMaterial.name))
        self.numericalAperture.setValue(numericalAperture)


    def _browseReflection(self):
        self.ERExplorer.show()