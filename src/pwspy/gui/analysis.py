# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
import os
import sys

from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import (QApplication)
from PyQt5.QtWidgets import QMainWindow
from .dialogs import WorkingDirDialog
from .dockWidgets import CellSelectorDock, AnalysisSettingsDock, ResultsTableDock, PlottingWidget


class App(QMainWindow):
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
        action = toolBar.addAction(QtGui.QIcon(os.path.join('resources', 'folder.png')), "Set Path")
        action.triggered.connect(self.fileDialog.show)
        action2 = toolBar.addAction(QtGui.QIcon(os.path.join('resources', 'icon.png')), "Idea")
        action2.triggered.connect(self.cellSelector.clearCells)
        toolBar.addAction(QtGui.QIcon(os.path.join('resources', 'playicon.svg')), 'Run')
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


def isIpython():
    try:
        return __IPYTHON__
    except:
        return False


if __name__ == '__main__':
    if isIpython():
        app = App()
    else:
        print("Not Ipython")
        app = QApplication(sys.argv)
        ex = App()
        sys.exit(app.exec_())
