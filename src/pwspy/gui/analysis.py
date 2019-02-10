# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
import sys
import os
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QDockWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QTableWidget,QTableWidgetItem, QVBoxLayout,
                             QTabWidget, QTextEdit, QLabel, QGroupBox,
                             QGridLayout)

from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
 
class App(QMainWindow):
 
    def __init__(self):
        super().__init__()
        self.title = 'PWS Analysis 2'
        self.left = 100
        self.top = 100
        self.width = 640
        self.height = 480
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
#        self.setStyleSheet("QMainWindow{background-color: gray} QFrame { border: 5px solid black } ")
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(4)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setItem(0,0, QTableWidgetItem("Cell (1,1)"))
        
        self.resultsTable = QTableWidget()
        self.resultsTable.setRowCount(5)
        self.resultsTable.setColumnCount(5)
        self.resultsTable.setItem(1,1,QTableWidgetItem("rms"))
        
        self.analysisSettings = QGroupBox();
        self.analysisSettings.setLayout(QVBoxLayout())
        self.analysisSettings.layout().addWidget(QLabel('hey'))
        self.analysisSettings.layout().addWidget(QTextEdit('1999'))
        
        self.plottingTab = QGroupBox()
        self.plottingTab.setLayout(QGridLayout())
        self.fig = Figure()
        ax = self.fig.add_subplot(1,1,1)
        ax.imshow(np.ones((100,100))*np.sin(np.linspace(1,6,num=100))[None,:])
        canvas = FigureCanvas(self.fig)
        self.plottingTab.layout().addWidget(canvas)
        self.plottingTab.layout().addWidget(NavigationToolbar(canvas, self.plottingTab))
        
        
#        c = QGroupBox()
#        c.setMaximumWidth(5)
#        self.setCentralWidget(c)
        d=QDockWidget('Cell Selection')
        d.setWidget(self.tableWidget)
        d2 = QDockWidget("Plotting")
        d2.setWidget(self.plottingTab)
        d3=QDockWidget('Settings')
        d3.setWidget(self.analysisSettings)
        d4 = QDockWidget("Results")
        d4.setWidget(self.resultsTable)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, d)
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, d2)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, d3)
        self.addDockWidget(QtCore.Qt.BottomDockWidgetArea,d4)
#        self.setDockNestingEnabled(True)
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)
        self.show()
 
    
def isIpython():
    try:
        return __IPYTHON__
    except:
        return False
    
if __name__ == '__main__':
    if isIpython():
        app = App()
    else:
        app = QApplication(sys.argv)
        ex = App()
        sys.exit(app.exec_())