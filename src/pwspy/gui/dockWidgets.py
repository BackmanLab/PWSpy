# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 18:51:35 2019

@author: Nick
"""
from PyQt5.QtWidgets import (QDockWidget, QTableWidget, QTableWidgetItem,
                             QGroupBox, QGridLayout, QLabel, QLineEdit,
                             QRadioButton, QFrame, QHBoxLayout, QVBoxLayout,
                             QScrollArea, QWidget, QDialog, QSpinBox,
                             QFileDialog, QPushButton, QApplication)
from PyQt5 import (QtCore, QtGui)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
import numpy as np
import matplotlib as mpl


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
        self.presets()
        self.hardWareCorrections()

        self.setWidget(self.widget)
        
    def presets(self):
        self.presets = QGroupBox("Presets")
        self.presets.setLayout(QHBoxLayout())
        self.presets.layout().addWidget(QRadioButton("Legacy"))
        self.presets.layout().addWidget(QRadioButton("Reccommended"))
        self.layout.addWidget(self.presets,0,0,1,2)

    def hardWareCorrections(self):
        self.hardWareCorrections = QGroupBox("Hardware Corrections")
        self.hardWareCorrections.setLayout(QGridLayout())
        _ = self.hardWareCorrections.layout().addWidget
        _(QLabel('DarkCounts'),0,0); _(QSpinBox(),0,1);
        _(QLabel("Linearity Correction"),0,2); _(QLineEdit(),0,3)
        frame = QFrame(); frame.setLayout(QHBoxLayout())
        frame.layout().addWidget(QPushButton())
        frame.layout().addWidget(QLineEdit())
        _(frame,1,0,1,4)
        self.layout.addWidget(self.hardWareCorrections,1,0,2,2)
        
class ResultsTable(QDockWidget):
    def __init__(self):
        super().__init__("Results")
        self.table = CopyableTable()
        self.table.setRowCount(5)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['RMS','LD'])
        self.table.setItem(1,1,QTableWidgetItem("rms"))
        self.setWidget(self.table)
    def copy(self):
        for i in range(self.table.rowCount):
            for j in range(self.table.columnCount):
                if self.table.cellWidget(i,j).isSelected():
                    print('a')
        
        
class PlottingWidget(QDockWidget):
    def __init__(self):
        super().__init__("Plotting")
        self.widget = QScrollArea()
        self.widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.widget.setWidgetResizable(True)
        self.m = QFrame()
        self.m.setLayout(QVBoxLayout())
        for i in range(4):
            self.m.layout().addWidget(LittlePlot())
        self.widget.setWidget(self.m)

        self.setWidget(self.widget)
        
class LittlePlot(FigureCanvas):
    def __init__(self):
#        self.setLayout(QGraphicsLinearLayout())
        self.fig = Figure()
        self.data = np.ones((100,100))*np.sin(np.linspace(1,6,num=100))[None,:]
        ax = self.fig.add_subplot(1,1,1)
        ax.imshow(self.data)
        ax.yaxis.set_visible(False)
        ax.xaxis.set_visible(False)
#        canvas = FigureCanvas(self.fig)
        super().__init__(self.fig)
#        self.layout().addWidget(canvas)
#        self.setFixedSize(200,200)
        self.mpl_connect("button_release_event", self.mouseReleaseEvent)
    def mouseReleaseEvent(self, event):
        BigPlot(self.data)

class BigPlot(QWidget):
    def __init__(self, data):
        super().__init__()
        self.setLayout(QGridLayout())
        self.fig = Figure()
        ax = self.fig.add_subplot(1,1,1)
        ax.imshow(data)
        canvas = FigureCanvas(self.fig)
        self.layout().addWidget(canvas)
        self.layout().addWidget(NavigationToolbar(canvas, self))
        self.show()
 
class CopyableTable(QTableWidget):
    def __init__(self):
        super().__init__()
        
    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy()
        else:
            super().keyPressEvent(event)
    def copy(self):
        try:
            sel = self.selectedRanges()[0]
            t = '\t'.join([self.horizontalHeaderItem(i).text() for i in range(self.columnCount())]) + '\n'
            for i in range(sel.topRow(), sel.bottomRow()+1):
                t +=  self.verticalHeaderItem(i).text()+ '\t'
                for j in range(sel.leftColumn(), sel.rightColumn()+1):
                    t += '\t'
                    item = self.item(i,j)
                    if not item is None:
                        t += item.text()                    
                t += '\n'
            QApplication.clipboard().setText(t)
        except Exception as e:
            print("Copy Failed: ",e)