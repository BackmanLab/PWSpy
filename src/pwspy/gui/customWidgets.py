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
                             QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QMenu, QHBoxLayout,
                             QPushButton, QLabel, QFrame)
from PyQt5 import (QtGui, QtCore)
import typing

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
   
class CellTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        columns = ('Cell','ROIs','Analyses', 'Notes', 'Plots')
        self.setRowCount(5)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.verticalHeader().hide()
        self.cells=[]
        '''Test'''
        for j in range(self.rowCount()):
            self.cells.append(CellTableWidgetItem(self, j, None, j))
#        self.table.setItem(1,1,QTableWidgetItem("rms"))
    def showContextMenu(self, point:QtCore.QPoint):
        menu = QMenu("Context Menu")
        action = menu.addAction("Disable cell")
        action.triggered.connect(self.toggleSelectedCellsInvalid)
        menu.exec(self.mapToGlobal(point))
        
    def toggleSelectedCellsInvalid(self):
        sel = self.selectedCells()
        state = not sel[0].isInvalid()
        for i in sel:
            i.setInvalid(state)
    def selectedCells(self) -> typing.List[int]:
        '''Returns the rows that have been selected.'''
        rowIndices = [i.row() for i in self.selectedIndexes()[::self.columnCount()]]
        rowIndices.sort()
        return [self.cells[i] for i in rowIndices]
    

class CellTableWidgetItem:
    def __init__(self,parent:CellTableWidget, row:int, cube, num:int):
#        super().__init__()
        self.parent = parent
        self.row=row
        self.plotsButton = QPushButton("show")
        self.notesButton = QPushButton("open")
        self.label = QTableWidgetItem(f"Cell{num}")
        
        self.parent.setItem(row,0,self.label)
        self.parent.setItem(row, 1, QTableWidgetItem(str(3)))#len(cube.getMasks())))
        self.parent.setItem(row, 2, QTableWidgetItem(str(1)))
        self.parent.setCellWidget(row, 3, self.notesButton)
        self.parent.setCellWidget(row, 4, self.plotsButton)
        
        self._invalid = False
        
    def setInvalid(self,invalid:bool):
        if invalid:
            self.label.setBackground(QtCore.Qt.red)
        else:
            self.label.setBackground(QtCore.Qt.white)
        self._invalid = invalid
    def isInvalid(self) -> bool :
        return self._invalid