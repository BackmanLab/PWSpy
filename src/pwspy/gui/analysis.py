# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
import os
import typing

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QApplication

from pwspy import ImCube
from pwspy.analysis.analysisClass import Analysis
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility import loadAndProcess
from .dialogs import WorkingDirDialog
from .dockWidgets import CellSelectorDock, AnalysisSettingsDock, ResultsTableDock, PlottingWidget
from . import resources

class PWSApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.window = PWSWindow()
        self.anMan = AnalysisManager(self)
        self.window.runAction.triggered.connect(self.anMan.run)

class PWSWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PWS Analysis 2')
        self.cellSelector = CellSelectorDock()
        self.analysisSettings = AnalysisSettingsDock()
        self.resultsTable = ResultsTableDock()
        self.plots = PlottingWidget(self.cellSelector.tableWidget)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.cellSelector)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plots)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.analysisSettings)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.resultsTable)
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        self.fileDialog = WorkingDirDialog(self)
        #        self.fileDialog.scanButtonPushed.connect(self.searchCells)

        menuBar = self.menuBar()
        view = menuBar.addMenu("View")
        view.addAction("Look at stuff")
        toolBar = self.addToolBar('tool')
        toolBar.setObjectName('mainToolBar()')
        browseAction = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'folder.png')), "Set Path")
        browseAction.triggered.connect(self.fileDialog.show)
        action2 = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'icon.png')), "Idea")
        action2.triggered.connect(self.cellSelector.clearCells)
        self.runAction = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'playicon.svg')), 'Run')
        settings = QtCore.QSettings("BackmanLab", "PWSAnalysis2");
        try:
            self.restoreGeometry(settings.value("geometry"));
            self.restoreState(settings.value("windowState"));
        except TypeError as e:  # Setting must not exist
            print(e)
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
        cellMetas = self.app.window.cellSelector.getSelectedCellMetas()
        self._checkMetaConsistency(cellMetas)
        settings = self.app.window.analysisSettings.getSettings()
        analysis = Analysis(settings)
        loadAndProcess([i.filePath for i in cellMetas], processorFunc=self._process, procArgs=[ref, analysis],
                       parallel=True)

    @staticmethod
    def _process(im: ImCube, ref: ImCube, analysis: Analysis):
        im.correctCameraEffects()
        results = analysis.run(im, ref)
        im.saveAnalysis(results, )

    @staticmethod
    def _checkMetaConsistency(cellMetas: typing.List[ICMetaData]):
        camCorrections = [i.cameraCorrection  for i in cellMetas]
        if None in camCorrections:
            #cell is missing automatic camera correction
        if len(set([hash(i) for i in camCorrections])) > 1:
            # multiple camera corrections are present.

