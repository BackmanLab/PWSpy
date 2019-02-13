# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
import sys
import os
import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QDockWidget
from PyQt5.QtWidgets import (QTableWidget,QTableWidgetItem, QVBoxLayout,
                             QTabWidget, QTextEdit, QLabel, QGroupBox,
                             QGridLayout, QApplication, QStyleFactory)

from dockWidgets import CellSelectorDock, AnalysisSettingsDock, ResultsTableDock, PlottingWidget


 
class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PWS Analysis 2')
        self.cellSelector = CellSelectorDock()
        self.analysisSettings = AnalysisSettingsDock()
        self.resultsTable = ResultsTableDock()
        self.plots = PlottingWidget()
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.cellSelector)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, self.plots)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.analysisSettings)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, self.resultsTable)
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)
        menuBar = self.menuBar()
        view = menuBar.addMenu("View")
        view.addAction("Look at stuff")
        toolBar = self.addToolBar('tool')
        toolBar.setObjectName('mainToolBar()')
        toolBar.addAction(QtGui.QIcon(os.path.join('resources','icon.png')),"Idea")
        toolBar.addAction(QtGui.QIcon(os.path.join('resources','playicon.svg')),'Run')
        settings = QtCore.QSettings("BackmanLab", "PWSAnalysis2");
        try:
            self.restoreGeometry(settings.value("geometry"));  
            self.restoreState(settings.value("windowState"));
        except AttributeError as e: #Setting must not exist
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