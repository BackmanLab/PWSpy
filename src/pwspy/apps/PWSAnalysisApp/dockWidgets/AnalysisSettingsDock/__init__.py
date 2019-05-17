from __future__ import annotations
import json
from typing import Tuple, List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, \
    QVBoxLayout, QPushButton, QSplitter, QMessageBox, QDialog, QGridLayout, QApplication

from pwspy.imCube import CameraCorrection
from pwspy.analysis import AnalysisSettings
import typing


if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.App import PWSApp
    from pwspy.apps.PWSAnalysisApp.dockWidgets import CellSelectorDock


from pwspy.imCube import ICMetaData
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from .widgets.QueueAnalysesFrame import AnalysisListItem, QueuedAnalysesFrame
from .widgets.SettingsFrame import SettingsFrame


class AnalysisSettingsDock(QDockWidget):
    def __init__(self, cellSelector: CellSelectorDock):
        super().__init__("Settings")
        self.app = QApplication.instance()
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.selector = cellSelector
        self.setObjectName('AnalysisSettingsDock')  # needed for restore state to work
        splitter = QSplitter(QtCore.Qt.Vertical, self)
        widg = QWidget()
        widg.setLayout(QVBoxLayout())
        self.settingsFrame = SettingsFrame(self.app.ERManager)
        widg.layout().addWidget(self.settingsFrame)
        self.addAnalysisButton = QPushButton("Add Analysis")
        widg.layout().addWidget(self.addAnalysisButton)
        widg2 = QWidget()
        widg2.setLayout(QVBoxLayout())
        self.analysesQueue = QueuedAnalysesFrame()
        self.analysesQueue.listWidget.itemDoubleClicked.connect(self.displayItemSettings)
        widg2.layout().addWidget(self.analysesQueue)

        self.addAnalysisButton.released.connect(self.addAnalysis)

        splitter.addWidget(widg)
        splitter.addWidget(widg2)
        splitter.setChildrenCollapsible(False)
        self.setWidget(splitter)

    def addAnalysis(self):
        try:
            camCorr = self.settingsFrame.getCameraCorrection()
            settings = self.settingsFrame.getSettings()
        except Exception as e:
            QMessageBox.information(self, 'Hold on', str(e))
            return
        self.analysesQueue.addAnalysis(self.settingsFrame.analysisName, camCorr, settings,
                                       self.selector.getSelectedReferenceMeta(),
                                       self.selector.getSelectedCellMetas())
    def loadFromSettings(self, settings: AnalysisSettings):
        self.settingsFrame.loadFromSettings(settings)

    def getAnalysisName(self):
        return self.settingsFrame.analysisName

    def getListedAnalyses(self) -> List[Tuple[str, AnalysisSettings, List[ICMetaData], ICMetaData, CameraCorrection, ERMetadata]]:
        return self.analysesQueue.analyses

    def displayItemSettings(self, item: AnalysisListItem):
        #Highlight relevant cells
        self.selector.setSelectedCells(item.cells)
        self.selector.setSelectedReference(item.reference)
        #Open a dialog
        # message = QMessageBox.information(self, item.name, json.dumps(item.settings.asDict(), indent=4))
        d = QDialog(self, (QtCore.Qt.WindowTitleHint | QtCore.Qt.Window))
        d.setModal(True)
        d.setWindowTitle(item.name)
        l = QGridLayout()
        setFrame = SettingsFrame(self.app.ERManager)
        setFrame.loadFromSettings(item.settings)
        setFrame.loadCameraCorrection(item.cameraCorrection)
        setFrame._analysisNameEdit.setText(item.name)
        setFrame._analysisNameEdit.setEnabled(False) # Don't allow changing the name.

        okButton = QPushButton("OK")
        okButton.released.connect(d.accept)

        l.addWidget(setFrame, 0, 0, 1, 1)
        l.addWidget(okButton, 1, 0, 1, 1)
        d.setLayout(l)
        d.show()
        d.exec()
        item.settings = setFrame.getSettings()
        item.cameraCorrection = setFrame.getCameraCorrection()

