import os
from glob import glob

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QDockWidget, QScrollArea, QFrame, QVBoxLayout, QSpacerItem, QSizePolicy, QGridLayout, \
    QGroupBox, QHBoxLayout, QRadioButton, QSpinBox, QLineEdit, QPushButton, QComboBox, QLabel, QDoubleSpinBox, \
    QCheckBox, QFileDialog, QWidget, QLayout

from pwspy.analysis import AnalysisSettings
from pwspy.gui import resources, applicationVars
from pwspy.gui.customWidgets import CollapsibleSection
from pwspy.utility import reflectanceHelper


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


class AnalysisSettingsDock(QDockWidget):
    def __init__(self):
        super().__init__("Settings")
        self.setObjectName('AnalysisSettingsDock')  # needed for restore state to work
        scroll = QScrollArea()
        self._frame = VerticallyCompressedWidget(self)
        self._frame.setLayout(QGridLayout())
        self._frame.setFixedWidth(350)
        scroll.setWidget(self._frame)
        self._layout = self._frame.layout()
        self.setupFrame()
        self.setWidget(scroll)
        self._updateSize()


    def setupFrame(self):
        """Presets"""
        row = 0
        self.analysisNameEdit = QLineEdit()
        self._layout.addWidget(QLabel("Analysis Name: "), row, 0, 1, 1)
        self._layout.addWidget(self.analysisNameEdit, row, 1, 1, 1)
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
        layout = QVBoxLayout()
        self.darkCountBox = QSpinBox()
        self.darkCountBox.setRange(0,10000)
        self.linearityEdit = QLineEdit()
        self.RSubtractionEdit = QLineEdit()
        self.RSubtractionBrowseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.png')), '')
        self.RSubtractionBrowseButton.released.connect(self._browseReflection)
        self.refMaterialCombo = QComboBox()
        self.refMaterialCombo.addItems([
            k for k in reflectanceHelper.materials.keys() if k != 'glass'])
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(QLabel('DarkCounts'))
        _(self.darkCountBox)
        _(QLabel("Linearity Correction"))
        _(self.linearityEdit)
        layout.addLayout(rLayout)
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(QLabel("R Subtraction"))
        _(self.RSubtractionEdit)
        _(self.RSubtractionBrowseButton)
        layout.addLayout(rLayout)
        rLayout = QHBoxLayout()
        _ = rLayout.addWidget
        _(QLabel("Reference Material"))
        _(self.refMaterialCombo)
        layout.addLayout(rLayout)
        self.hardwareCorrections = CollapsibleSection('Automatic Correction', 200, self)
        self.hardwareCorrections.stateChanged.connect(self._updateSize)
        self.hardwareCorrections.setLayout(layout)

        self._layout.addWidget(self.hardwareCorrections, row, 0, 1, 4)
        row += 1

        '''SignalPreparations'''
        self.signalPrep = QGroupBox("Signal Prep")
        self.signalPrep.setFixedSize(175, 75)
        layout = QGridLayout()
        _ = layout.addWidget
        self.filterOrder = QSpinBox()
        self.filterOrder.setRange(0,6)
        self.filterCutoff = QDoubleSpinBox()
        _(QLabel("Filter Order"), 0, 0, 1, 1)
        _(self.filterOrder, 0, 1, 1, 1)
        _(QLabel("Cutoff Freq."), 1, 0, 1, 1)
        _(self.filterCutoff, 1, 1, 1, 1)
        _(QLabel("nm<sup>-1</sup>"), 1, 2, 1, 1)
        self.signalPrep.setLayout(layout)
        self._layout.addWidget(self.signalPrep, row, 0, 1, 2)

        '''Cropping'''
        self.cropping = QGroupBox("Wavelength Cropping")
        self.cropping.setFixedSize(125,75)
        layout = QGridLayout()
        _ = layout.addWidget
        self.wavelengthStart = QSpinBox()
        self.wavelengthStop = QSpinBox()
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
        layout = QGridLayout()
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
        self.autoCorrStopIndex = QSpinBox()
        self.minSubCheckBox = QCheckBox("MinSub")
        self.hannWindowCheckBox = QCheckBox("Hanning Window")
        layout = QGridLayout()
        _ = layout.addWidget
        _(QLabel("AutoCorr Stop Index"), 0, 0, 1, 1)
        _(self.autoCorrStopIndex, 0, 1, 1, 1)
        _(self.minSubCheckBox, 1, 0, 1, 1)
        _(self.hannWindowCheckBox, 1, 1, 1, 1)
        self.advanced.setLayout(layout)
        self._layout.addWidget(self.advanced, row, 0, 1, 4)
        row += 1

    def loadFromSettings(self, settings: AnalysisSettings):
        self.filterOrder.setValue(settings.filterOrder)
        self.filterCutoff.setValue(settings.filterCutoff)
        self.polynomialOrder.setValue(settings.polynomialOrder)
        self.RSubtractionEdit.setText(settings.rInternalSubtractionPath)
        self.refMaterialCombo.setCurrentIndex(self.refMaterialCombo.findText(settings.referenceMaterial))
        self.wavelengthStop.setValue(settings.wavelengthStop)
        self.wavelengthStart.setValue(settings.wavelengthStart)
        self.advanced.setCheckState(2 if settings.skipAdvanced else 0)
        self.autoCorrStopIndex.setValue(settings.autoCorrStopIndex)
        self.minSubCheckBox.setCheckState(2 if settings.autoCorrMinSub else 0)
        self.hannWindowCheckBox.setCheckState(2 if settings.useHannWindow else 0)

    def _updateSize(self):
        height = 75  # give this much excess room.
        height += self.presets.height()
        height += self.hardwareCorrections.height()
        height += self.signalPrep.height()
        height += self.polySub.height()
        height += self.advanced.height()
        self._frame.setFixedHeight(height)

    def getSettings(self) -> AnalysisSettings:
        return AnalysisSettings(filterOrder=self.filterOrder.value(),
                                filterCutoff=self.filterCutoff.value(),
                                polynomialOrder=self.polynomialOrder.value(),
                                rInternalSubtractionPath=self.RSubtractionEdit.text(),
                                referenceMaterial=self.refMaterialCombo.currentText(),
                                wavelengthStart=self.wavelengthStart.value(),
                                wavelengthStop=self.wavelengthStop.value(),
                                skipAdvanced=self.advanced.checkState() != 0,
                                useHannWindow=self.hannWindowCheckBox.checkState() != 0,
                                autoCorrMinSub=self.minSubCheckBox.checkState() != 0,
                                autoCorrStopIndex=self.autoCorrStopIndex.value())

    def getAnalysisName(self):
        return self.analysisNameEdit.text()

    def _browseReflection(self):
        file, _filter = QFileDialog.getOpenFileName(self, 'Working Directory', applicationVars.dataDirectory, "HDF5 (*.h5 *.hdf5)")
        if file != '':
            self.RSubtractionEdit.setText(file)
