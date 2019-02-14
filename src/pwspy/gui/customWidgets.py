# -*- coding: utf-8 -*-
"""
Created on Mon Feb 11 21:22:01 2019

@author: Nick
"""
from matplotlib.figure import Figure
import numpy as np
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5.QtWidgets import (QWidget, QApplication, QGridLayout,
                             QTableWidget, QTableWidgetItem, QAbstractItemView)
from PyQt5 import (QtGui, QtCore)

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
        self.setMaximumWidth(200)
    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
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
        self.setSelectionMode(QAbstractItemView.ContiguousSelection)
    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy()
        else:
            super().keyPressEvent(event)
    def copy(self):
        try:
            sel = self.selectedRanges()[0]
            t = '\t'.join([self.horizontalHeaderItem(i).text() for i in range(sel.leftColumn(), sel.rightColumn()+1)]) + '\n'
            for i in range(sel.topRow(), sel.bottomRow()+1):
                for j in range(sel.leftColumn(), sel.rightColumn()+1):
                    if t[-1]!='\n': t += '\t'
                    item = self.item(i,j)
                    t += ' ' if item is None else item.text()                    
                t += '\n'
            QApplication.clipboard().setText(t)
        except Exception as e:
            print("Copy Failed: ",e)
            
class CellTableWidgetItem(QTableWidgetItem):
    def __init__(self):
        super().__init__()
        
    def setInvalid(self,invalid:bool):
        if invalid:
            self.setBackground(QtCore.Qt.red)
        else:
            self.setBackground(QtCore.Qt.white)