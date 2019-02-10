# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
import sys
import os
import numpy as np
from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QTableWidget,QTableWidgetItem, QVBoxLayout,
                             QTabWidget, QTextEdit, QLabel, QGroupBox,
                             QGridLayout)

from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
 
class App(QWidget):
 
    def __init__(self):
        super().__init__()
        self.title = 'PWS Analysis 2'
        self.left = 100
        self.top = 100
        self.width = 640
        self.height = 480
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(4)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setItem(0,0, QTableWidgetItem("Cell (1,1)"))
        
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
        
        
        # Add box layout, add table to box layout and add box layout to widget
        self.layout = QVBoxLayout()
        tab = QTabWidget()
        tab.addTab(self.tableWidget, 'cells')
        tab.addTab(self.analysisSettings,'sett')
        tab.addTab(self.plottingTab, 'plot')
        self.layout.addWidget(tab)
        self.setLayout(self.layout) 
        
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