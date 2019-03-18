# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
import os
import shutil
import typing

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox

from pwspy import ImCube, CameraCorrection
from pwspy.analysis.analysisClass import Analysis
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.analysis import defaultSettingsPath
from pwspy.utility import loadAndProcess
from .dialogs import WorkingDirDialog
from .dockWidgets import CellSelectorDock, AnalysisSettingsDock, ResultsTableDock, PlottingDock
from . import resources
from . import applicationVars
from glob import glob

class PWSApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self._setupDataDirectories()
        self.window = PWSWindow()
        self.anMan = AnalysisManager(self)
        self.window.runAction.triggered.connect(self.anMan.run)

    @staticmethod
    def _setupDataDirectories():
        if not os.path.exists(applicationVars.dataDirectory):
            os.mkdir(applicationVars.dataDirectory)
        if not os.path.exists(applicationVars.analysisSettingsDirectory):
            os.mkdir(applicationVars.analysisSettingsDirectory)
            settingsFiles = glob(os.path.join(defaultSettingsPath, '*.json'))
            for f in settingsFiles:
                shutil.copyfile(f, os.path.join(applicationVars.analysisSettingsDirectory, os.path.split(f)[-1]))
        if not os.path.exists(applicationVars.extraReflectionDirectory):
            os.mkdir(applicationVars.extraReflectionDirectory)



class PWSWindow(QMainWindow):
    def __init__(self):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        super().__init__()
        self.setWindowTitle('PWS Analysis 2')
        self.cellSelector = CellSelectorDock()
        self.analysisSettings = AnalysisSettingsDock(self.cellSelector)
        self.resultsTable = ResultsTableDock()
        self.plots = PlottingDock(self.cellSelector)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.cellSelector)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plots)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.analysisSettings)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.resultsTable)
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        self.fileDialog = WorkingDirDialog(self)

        # menuBar = self.menuBar()
        # view = menuBar.addMenu("View")
        # view.addAction("Look at stuff")
        toolBar = self.addToolBar('tool')
        toolBar.setObjectName('mainToolBar()')
        browseAction = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'folder.png')), "Set Path")
        browseAction.triggered.connect(self.fileDialog.show)
        action2 = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'icon.png')), "Idea")
        action2.triggered.connect(self.cellSelector.clearCells)
        self.runAction = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'playicon.svg')), 'Run')
        settings = QtCore.QSettings("BackmanLab", "PWSAnalysis2")
        try:
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))
        except TypeError as e:  # Setting must not exist
            self.resize(1024, 768)
        self.show()

    def closeEvent(self, event):
        settings = QtCore.QSettings("BackmanLab", "PWSAnalysis2")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        super().closeEvent(event)


class AnalysisManager:
    def __init__(self, app: PWSApp):
        self.app = app

    def run(self):
        refMeta = self.app.window.cellSelector.getSelectedReferenceMeta()
        cellMetas = self.app.window.cellSelector.getSelectedCellMetas()
        if self._checkMetaConsistency(cellMetas): # If the metadata looks ok to proceed
            ref = ImCube.fromMetadata(refMeta)
            cameraCorrection, settings = self.app.window.analysisSettings.getSettings()
            if cameraCorrection is not None:
                ref.correctCameraEffects(cameraCorrection)
            else:
                print("Using automatically detected camera corrections")
                ref.correctCameraEffects(ref.cameraCorrection)
            analysis = Analysis(settings, ref)
            analysisName = self.app.window.analysisSettings.getAnalysisName()
            loadAndProcess(cellMetas, processorFunc=self._process, procArgs=[ref, analysis, analysisName],
                                 parallel=True)

    @staticmethod
    def _process(im: ImCube, analysis: Analysis, analysisName: str, cameraCorrection: CameraCorrection):
        if cameraCorrection is not None:
            im.correctCameraEffects(cameraCorrection)
        else:
            im.correctCameraEffects(im.cameraCorrection)
        results = analysis.run(im)
        im.saveAnalysis(results, analysisName)

    def _checkMetaConsistency(self, cellMetas: typing.List[ICMetaData]) -> bool:
        camCorrections = [i.cameraCorrection for i in cellMetas]
        if None in camCorrections:
            QMessageBox.information(self.app.window, 'Hmm', 'Cell is missing automatic camera correction')
            return False
        if len(set([hash(i) for i in camCorrections])) > 1:
            QMessageBox.information(self.app.window, 'Hmm', "Multiple camera corrections are present in the set of selected cells.")
            return False
        return True

