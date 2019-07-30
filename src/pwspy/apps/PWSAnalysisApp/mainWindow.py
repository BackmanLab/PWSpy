import os

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QApplication, QToolBar, QMessageBox
from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
from . import resources
from pwspy.apps import resources as sharedresources
from .dialogs import WorkingDirDialog
from ._dockWidgets import CellSelectorDock, AnalysisSettingsDock, ResultsTableDock, PlottingDock
from .blinder import BlinderDialog

class PWSWindow(QMainWindow):
    def __init__(self, erManager: ERManager):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        super().__init__()
        self.setWindowTitle('PWS Analysis v2')
        self.setWindowIcon(QtGui.QIcon(os.path.join(resources, 'cellLogo.png')))
        self.cellSelector = CellSelectorDock()
        self.analysisSettings = AnalysisSettingsDock(self.cellSelector, erManager)
        self.resultsTable = ResultsTableDock()
        self.plots = PlottingDock(self.cellSelector)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.cellSelector)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plots)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.analysisSettings)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.resultsTable)
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        self.fileDialog = WorkingDirDialog(self)

        menuBar = self.menuBar()
        menu = menuBar.addMenu("Menu")
        defaultLayoutAction = menu.addAction("Set Default Layout")
        defaultLayoutAction.triggered.connect(self._setDefaultLayout)
        self.parallelAction = menu.addAction("Multi-Core Analysis")
        self.parallelAction.setCheckable(True)
        self.parallelAction.setChecked(True)
        infoAction = menu.addAction("Info")
        infoAction.triggered.connect(self.openInfoPane)
        self.blindAction = menu.addAction("Create blinded directory")
        toolBar = QToolBar("Tool Bar", self)
        toolBar.setFloatable(False)
        toolBar.setObjectName('mainToolBar()')
        self.addToolBar(QtCore.Qt.LeftToolBarArea, toolBar)
        browseAction = toolBar.addAction(QtGui.QIcon(os.path.join(sharedresources, 'folder.svg')), "Set Path")
        browseAction.triggered.connect(self.fileDialog.show)
        self.runAction = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'playicon.svg')), 'Run').triggered
        settings = QtCore.QSettings("BackmanLab", "PWSAnalysis2")
        try:
            self.restoreGeometry(settings.value("geometry"))
            self.restoreState(settings.value("windowState"))
        except TypeError as e:  # Setting must not exist
            self.resize(1024, 768)
            self._setDefaultLayout()
        self.show()

    def closeEvent(self, event):
        settings = QtCore.QSettings("BackmanLab", "PWSAnalysis2")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        self.cellSelector.clearCells() #This causes the current cell items to save their metadata.
        super().closeEvent(event)

    def openInfoPane(self):
        msgBox = QMessageBox.information(self, "About PWS Analysis V2", "This software is intended for the analysis of Partial Wave Spectroscopic microscopy data.")

    def _setDefaultLayout(self):
        #remove all docks then re add them
        docks = [self.cellSelector, self.plots, self.analysisSettings, self.resultsTable]
        for dock in docks:
            self.removeDockWidget(dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.cellSelector)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plots)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.resultsTable)
        self.tabifyDockWidget(self.plots, self.analysisSettings)
        for dock in docks:
            dock.setVisible(True)
