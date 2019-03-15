import os
from glob import glob
from typing import Tuple, Optional, List

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPalette, QValidator
from PyQt5.QtWidgets import QDockWidget, QScrollArea, QGridLayout, QLineEdit, QLabel, QGroupBox, QHBoxLayout, QWidget, \
    QRadioButton, QFrame, QVBoxLayout, QSpinBox, QPushButton, QComboBox, QDoubleSpinBox, QCheckBox, QFileDialog, \
    QMessageBox, QSplitter, QListWidget, QListWidgetItem, QMenu, QAction

from pwspy import CameraCorrection
from pwspy.analysis import AnalysisSettings
from pwspy.gui import applicationVars, resources
from pwspy.gui.dockWidgets import CellSelectorDock
from pwspy.gui.dockWidgets.AnalysisSettingsDock.widgets import LinearityValidator
from pwspy.imCube.ICMetaDataClass import ICMetaData
from .widgets import VerticallyCompressedWidget
from pwspy.gui.sharedWidgets import CollapsibleSection
from pwspy.utility import reflectanceHelper

class SettingsFrame(QScrollArea):
    def __init__(self):
        super().__init__()
        self._frame = VerticallyCompressedWidget(self)
        self._layout = QGridLayout()
        self._frame.setLayout(self._layout)
        self._frame.setFixedWidth(350)
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
        self.linearityEdit.setValidator(LinearityValidator())
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
        self.hardwareCorrections.setLayout(layout)
        self._layout.addWidget(self.hardwareCorrections, row, 0, 1, 4)
        row += 1

        '''Extra Reflection'''
        self.extraReflection = QGroupBox("Extra Reflection")
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        self.RSubtractionEdit = QLineEdit()
        self.RSubtractionBrowseButton = QPushButton(QtGui.QIcon(os.path.join(resources, 'folder.png')), '')
        self.RSubtractionBrowseButton.released.connect(self._browseReflection)
        self.refMaterialCombo = QComboBox()
        self.refMaterialCombo.addItems([
            k for k in reflectanceHelper.materials.keys() if k != 'glass'])
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
        self.extraReflection.setLayout(layout)
        self._layout.addWidget(self.extraReflection, row, 0, 1, 4)
        row += 1

        '''SignalPreparations'''
        self.signalPrep = QGroupBox("Signal Prep")
        self.signalPrep.setFixedSize(175, 75)
        layout = QGridLayout()
        layout.setContentsMargins(1, 1, 1, 1)
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
        layout.setContentsMargins(1, 1, 1, 1)
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
        layout.setContentsMargins(1, 1, 1, 1)
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

        self._updateSize()

    def _updateSize(self):
        height = 100  # give this much excess room.
        height += self.presets.height()
        height += self.hardwareCorrections.height()
        height += self.extraReflection.height()
        height += self.signalPrep.height()
        height += self.polySub.height()
        height += self.advanced.height()
        self._frame.setFixedHeight(height)

    def loadFromSettings(self, settings: AnalysisSettings):
        self.filterOrder.setValue(settings.filterOrder)
        self.filterCutoff.setValue(settings.filterCutoff)
        self.polynomialOrder.setValue(settings.polynomialOrder)
        self.RSubtractionEdit.setText(settings.extraReflectionPath)
        self.refMaterialCombo.setCurrentIndex(self.refMaterialCombo.findText(settings.referenceMaterial))
        self.wavelengthStop.setValue(settings.wavelengthStop)
        self.wavelengthStart.setValue(settings.wavelengthStart)
        self.advanced.setCheckState(2 if settings.skipAdvanced else 0)
        self.autoCorrStopIndex.setValue(settings.autoCorrStopIndex)
        self.minSubCheckBox.setCheckState(2 if settings.autoCorrMinSub else 0)
        self.hannWindowCheckBox.setCheckState(2 if settings.useHannWindow else 0)

    def getSettings(self) -> Tuple[CameraCorrection, AnalysisSettings]:
        if self.linearityEdit.validator().state != QValidator.Acceptable:
            QMessageBox.information(self, "Hold On", "The camera linearity correction input is not valid.")
            raise ValueError("The camera linearity correction input is not valid.")
        linText = self.linearityEdit.text()
        linearityPoly = tuple(float(i) for i in linText.split(',')) if linText != '' else None
        if self.hardwareCorrections.checkState() == 0:
            cameraCorrection = CameraCorrection(self.darkCountBox.value(), linearityPoly)
        else:
            cameraCorrection = None
        return (cameraCorrection,
                AnalysisSettings(filterOrder=self.filterOrder.value(),
                                 filterCutoff=self.filterCutoff.value(),
                                 polynomialOrder=self.polynomialOrder.value(),
                                 extraReflectionPath=self.RSubtractionEdit.text(),
                                 referenceMaterial=self.refMaterialCombo.currentText(),
                                 wavelengthStart=self.wavelengthStart.value(),
                                 wavelengthStop=self.wavelengthStop.value(),
                                 skipAdvanced=self.advanced.checkState() != 0,
                                 useHannWindow=self.hannWindowCheckBox.checkState() != 0,
                                 autoCorrMinSub=self.minSubCheckBox.checkState() != 0,
                                 autoCorrStopIndex=self.autoCorrStopIndex.value()))

    def _browseReflection(self):
        file, _filter = QFileDialog.getOpenFileName(self, 'Working Directory',
                                                    applicationVars.extraReflectionDirectory,
                                                    "HDF5 (*.h5 *.hdf5)")
        if file != '':
            self.RSubtractionEdit.setText(file)


class AnalysisListItem(QListWidgetItem):
    def __init__(self, cameraCorrection: CameraCorrection, settings: AnalysisSettings, reference: ICMetaData, cells: List[ICMetaData], label: str,
                 parent: Optional[QWidget] = None):
        super().__init__(label, parent)
        self.cameraCorrection = cameraCorrection
        self.settings = settings
        self.reference = reference
        self.cells = cells


class QueuedAnalyses(QScrollArea):
    def __init__(self):
        super().__init__()
        self.listWidget = QListWidget()
        self.setWidget(self.listWidget)
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)
        self.listWidget.itemDoubleClicked.connect( # TODO display settings)

    def addAnalysis(self, cameraCorrection: CameraCorrection, settings: AnalysisSettings, reference: ICMetaData, cells: List[ICMetaData]):
        item = AnalysisListItem(cameraCorrection, settings, reference, cells, 'BlahBlah', self.listWidget)
        self.listWidget.addItem(item)

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        deleteAction = QAction("Delete", self)
        deleteAction.triggered.connect(self.deleteSelected)
        menu.addAction(deleteAction)
        menu.exec(self.mapToGlobal(point));


class AnalysisSettingsDock(QDockWidget):
    def __init__(self, cellSelector: CellSelectorDock):
        super().__init__("Settings")
        self.selector = cellSelector
        self.setObjectName('AnalysisSettingsDock')  # needed for restore state to work
        splitter = QSplitter(QtCore.Qt.Vertical, self)
        widg = QWidget()
        widg.setLayout(QVBoxLayout())
        self.settingsFrame = SettingsFrame()
        widg.layout().addWidget(self.settingsFrame)
        self.addAnalysisButton = QPushButton("Add Analysis")
        widg.layout().addWidget(self.addAnalysisButton)
        self.analysesQueue = QueuedAnalyses()

        self.addAnalysisButton.released.connect(
            lambda: self.analysesQueue.addAnalysis(*self.settingsFrame.getSettings(),
                                                   self.selector.getSelectedReferenceMeta(),
                                                   self.selector.getSelectedCellMetas()))
        self.analysesQueue.listWidget.currentItemChanged.connect(#TODO Highlight cells and ref)


        splitter.addWidget(widg)
        splitter.addWidget(self.analysesQueue)
        splitter.setChildrenCollapsible(False)
        self.setWidget(splitter)

    def loadFromSettings(self, settings: AnalysisSettings):
        self.settingsFrame.loadFromSettings(settings)

    def getSettings(self) -> Tuple[CameraCorrection, AnalysisSettings]:
        return self.settingsFrame.getSettings()

    def getAnalysisName(self):
        return self.settingsFrame._analysisNameEdit.text()
