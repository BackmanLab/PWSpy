# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

import os

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QMainWindow, QApplication, QToolBar, QMessageBox
from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
from . import resources
from pwspy.apps import resources as sharedresources
import pwspy
from .dialogs import WorkingDirDialog
from ._dockWidgets import CellSelectorDock, AnalysisSettingsDock, ResultsTableDock, PlottingDock


class PWSWindow(QMainWindow):
    def __init__(self, erManager: ERManager):
        super().__init__()
        self.setWindowTitle(QApplication.instance().applicationName())
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
        menu = menuBar.addMenu("View")
        defaultLayoutAction = menu.addAction("Set Default Layout")
        defaultLayoutAction.triggered.connect(self._setDefaultLayout)
        infoAction = menu.addAction("Info")
        infoAction.triggered.connect(self.openInfoPane)
        menu = menuBar.addMenu("Config")
        self.parallelAction = menu.addAction("Multi-Core Analysis (faster, needs more RAM)")
        self.parallelAction.setCheckable(True)
        menu = menuBar.addMenu("Actions")
        menu.setToolTipsVisible(True)
        self.blindAction = menu.addAction("Create blinded directory")
        self.blindAction.setToolTip("Creates a folder of symlinks to the selected data that is randomly numbered. "
                                    "This allows you to work on data anonymously without bias. You may need to run this "
                                    "software as `Admin` for this to work on Windows.")
        self.roiConvertAction = menu.addAction("Update ROI file formats")
        self.roiConvertAction.setToolTip("Updates old .MAT roi files to a newer .H5 format that will run more efficiently."
                                         " Warning: The old files will be deleted.")

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
        msgBox = QMessageBox.information(self, "About PWS Analysis", f"This software is intended for the analysis of Partial Wave Spectroscopic microscopy data.\npwspy version: {pwspy.__version__}")

    def _setDefaultLayout(self):
        #remove all docks then re add them
        docks = [self.cellSelector, self.plots, self.analysisSettings, self.resultsTable]
        for dock in docks:
            self.removeDockWidget(dock)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.cellSelector)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plots)
        #self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.resultsTable)
        self.tabifyDockWidget(self.cellSelector, self.resultsTable)
        self.tabifyDockWidget(self.plots, self.analysisSettings)
        for dock in docks:
            dock.setFloating(False)
            dock.setVisible(True)
