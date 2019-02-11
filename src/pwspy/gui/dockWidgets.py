# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 18:51:35 2019

@author: Nick
"""
from PyQt5.QtWidgets import (QDockWidget, QTableWidget, QTableWidgetItem,
                             QGroupBox, QGridLayout, QLabel, QTextEdit,
                             QRadioButton, QFrame, QHBoxLayout, QVBoxLayout,
                             QScrollArea)
from PyQt5 import QtCore
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import numpy as np


class CellSelector(QDockWidget):
    def __init__(self):
        super().__init__("Cell Selector")
        self.tableWidget = QTableWidget()
        self.tableWidget.setRowCount(4)
        self.tableWidget.setColumnCount(1)
        self.tableWidget.setItem(0,0, QTableWidgetItem("Cell (1,1)"))
        self.setWidget(self.tableWidget)
    
class AnalysisSettings(QDockWidget):
    def __init__(self):
        super().__init__("Settings")
        self.widget = QFrame()
        self.layout = QGridLayout()
        self.widget.setLayout(self.layout)
        
        self.presets = QGroupBox("Presets")
        self.presets.setLayout(QHBoxLayout())
        self.presets.layout().addWidget(QRadioButton("Legacy"))
        self.presets.layout().addWidget(QRadioButton("Reccomendieed"))
        self.layout.addWidget(self.presets)
        self.layout.addWidget(QLabel('DarkCounts'))
        self.layout.addWidget(QTextEdit())
        self.layout.addWidget(QLabel('etc'))
        self.setWidget(self.widget)
        
class ResultsTable(QDockWidget):
    def __init__(self):
        super().__init__("Results")
        self.resultsTable = QTableWidget()
        self.resultsTable.setRowCount(5)
        self.resultsTable.setColumnCount(5)
        self.resultsTable.setItem(1,1,QTableWidgetItem("rms"))
        self.setWidget(self.resultsTable)
        
        
class PlottingWidget(QDockWidget):
    def __init__(self):
        super().__init__("Plotting")
        self.widget = QScrollArea()
        self.widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.m = QFrame()
        self.m.setLayout(QVBoxLayout())
        for i in range(4):
            self.m.layout().addWidget(Plot())
        self.widget.setWidget(self.m)

        self.setWidget(self.widget)
        
class Plot(QFrame):
    def __init__(self):
        super().__init__()
        self.setLayout(QGridLayout())
        self.fig = Figure()
        ax = self.fig.add_subplot(1,1,1)
        ax.imshow(np.ones((100,100))*np.sin(np.linspace(1,6,num=100))[None,:])
        canvas = FigureCanvas(self.fig)
#        canvas.setMinimumHeight(700)
        self.layout().addWidget(canvas)
        self.layout().addWidget(NavigationToolbar(canvas, self))
        self.setFixedSize(512,512)
#        self.setMinimumHeight(200)
        