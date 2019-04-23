import os

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QApplication

from . import resources
from pwspy.apps import resources as sharedresources
from .dialogs import WorkingDirDialog
from .dockWidgets import CellSelectorDock, AnalysisSettingsDock, ResultsTableDock, PlottingDock


class PWSWindow(QMainWindow):
    def __init__(self):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        super().__init__()
        self.setWindowTitle('PWS Analysis v2')
        self.setWindowIcon(QtGui.QIcon(os.path.join(resources, 'cellLogo.png')))
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
        self.fileDialog.directoryChanged.connect(lambda directory: self.setWindowTitle(f'PWS Analysis v2 - {directory}'))

        menuBar = self.menuBar()
        view = menuBar.addMenu("View")
        act = view.addAction("Set Default Layout")
        act.triggered.connect(self._setDefaultLayout)
        toolBar = self.addToolBar('tool')
        toolBar.setObjectName('mainToolBar()')
        browseAction = toolBar.addAction(QtGui.QIcon(os.path.join(sharedresources, 'folder.svg')), "Set Path")
        browseAction.triggered.connect(self.fileDialog.show)
        action2 = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'icon.png')), "Idea")
        # action2.triggered.connect(self.cellSelector.clearCells) #This was just for testing
        self.runAction = toolBar.addAction(QtGui.QIcon(os.path.join(resources, 'playicon.svg')), 'Run')
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
        self
        super().closeEvent(event)

    def _setDefaultLayout(self):
        #remove all docks then re add them
        docks = [self.cellSelector, self.plots, self.analysisSettings, self.resultsTable]
        for dock in docks:
            self.removeDockWidget(dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.cellSelector)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plots)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.resultsTable)
        self.tabifyDockWidget(self.plots, self.analysisSettings)
        # self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.analysisSettings)
        for dock in docks:
            dock.setVisible(True)
