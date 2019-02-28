# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 18:51:35 2019

@author: Nick
"""
from PyQt5.QtWidgets import (QDockWidget, QTableWidget, QTableWidgetItem,
                             QGroupBox, QGridLayout, QLabel, QLineEdit,
                             QRadioButton, QFrame, QHBoxLayout, QVBoxLayout,
                             QScrollArea, QWidget, QDialog, QSpinBox,
                             QFileDialog, QPushButton, QApplication,
                             QCheckBox, QSizePolicy, QSpacerItem, QMessageBox,
                             QComboBox)
from PyQt5 import (QtCore, QtGui)
from customWidgets import CopyableTable, LittlePlot, CellTableWidget, CollapsibleSection, AspectRatioWidget, CellTableWidgetItem
from pwspy.analysis import AnalysisSettings
import os
from pwspy.imCube.ICMetaDataClass import ICMetaData
import re
from collections.abc import Iterable


class CellSelectorDock(QDockWidget):
    def __init__(self):
        super().__init__("Cell Selector")
        self.setObjectName('CellSelectorDock') #needed for restore state to work
        self.widget = QWidget(self)
        layout = QVBoxLayout()
        self.tableWidget = CellTableWidget(self.widget)
        self.filterWidget = QWidget(self.widget)
        self.pathFilter = QComboBox(self.filterWidget)
        self.pathFilter.currentTextChanged.connect(self.filterPath)
        self.pathFilter.setEditable(True)
        self.numberFilter = QLineEdit(self.filterWidget)
        self.numberFilter.editingFinished.connect(self.filterNumbers)
        _ = QGridLayout()
        _.addWidget(self.pathFilter,0,0,1,1)
        _.addWidget(self.numberFilter,0,1,1,1)
        self.filterWidget.setLayout(_)
        layout.addWidget(self.tableWidget)
        layout.addWidget(self.filterWidget)
        self.widget.setLayout(layout)
        self.setWidget(self.widget)
        self.cells = []
    def addCell(self, fileName:str, workingDir:str):
        self.cells.append(ICMetaData.loadAny(fileName))
        cell = CellTableWidgetItem(self.cells[-1], os.path.split(fileName)[0][len(workingDir)+1:], int(fileName.split('Cell')[-1]))
        self.tableWidget.addCellItem(cell)
    def clearCells(self):
        self.cells = []
        self.tableWidget.clearCellItems()
    def updateFilters(self):
        self.pathFilter.clear()
        self.pathFilter.addItem('.*')
        paths = []
        for i in self.tableWidget.cellItems:
            paths.append(i.path.text())
        self.pathFilter.addItems(set(paths))
    def filterPath(self, path:str):
#        path = r'{}'.format(path)
        path = path.replace('\\', '\\\\')
        for i in range(self.tableWidget.rowCount()):
#            text = r'{}'.format(self.tableWidget.item(i,0).text())
            text = self.tableWidget.item(i,0).text()
            text = text.replace(r'\\', r'\\\\')
            print(text, path)
            if re.match(path,text):
                self.tableWidget.setRowHidden(i,False)
            else:
                self.tableWidget.setRowHidden(i,True)
    def filterNumbers(self):
        pattern = self.numberFilter.text()
        try:
            ret = eval(pattern)
        except:
            QMessageBox.information(f'{pattern} is not a valid command.')
            return
        if not isinstance(ret, Iterable):
            QMessageBox.information(f'{pattern} does not generate an iterator.')
            return
    
class AnalysisSettingsDock(QDockWidget):
    def __init__(self):
        super().__init__("Settings")
        self.setObjectName('AnalysisSettingsDock') #needed for restore state to work
        self.widget = QScrollArea()
        self.internalWidget = QFrame()
        self.internalWidget.setLayout(QVBoxLayout())
        self.internalWidget.setFixedSize(350,400)

        self.contentsFrame = QFrame()
        self.contentsFrame.setMinimumSize(350,100)
        spacer = QSpacerItem(0,0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.internalWidget.layout().addWidget(self.contentsFrame)
        self.internalWidget.layout().addItem(spacer)
        self.widget.setWidget(self.internalWidget)
        self.layout = QGridLayout()#QVBoxLayout()
        self.contentsFrame.setLayout(self.layout)
        self.setupFrame()
        self.setWidget(self.widget)
        
    def setupFrame(self):
        '''Presets'''
        self.presets = QGroupBox("Presets")
        self.presets.setLayout(QHBoxLayout())
        self.presets.layout().addWidget(QRadioButton("Legacy"))
        self.presets.layout().addWidget(QRadioButton("Reccommended"))
        self.layout.addWidget(self.presets,0,0,1,4)

        '''Hardwarecorrections'''
        layout = QGridLayout()
        _ = layout.addWidget
        _(QLabel('DarkCounts'),0,0); _(QSpinBox(),0,1);
        _(QLabel("Linearity Correction"),0,2); _(QLineEdit(),0,3)
        frame = QFrame(); frame.setLayout(QHBoxLayout())
        frame.layout().addWidget(QLabel("R Subtraction"))
        frame.layout().addWidget(QLineEdit())
        frame.layout().addWidget(QPushButton())
        _(frame,1,0,1,4)
        self.hardwareCorrections = CollapsibleSection('Automatic Correction',100,self)
        self.hardwareCorrections.stateChanged.connect(self.updateSize)
        self.hardwareCorrections.setLayout(layout)

        self.layout.addWidget(self.hardwareCorrections,1,0,1,4)
        
        '''SignalPreparations'''
        self.signalPrep = QGroupBox("Signal Prep")
        self.signalPrep.setFixedSize(150,100)
        self.signalPrep.setLayout(QGridLayout())
        _ = self.signalPrep.layout().addWidget
        self.filterOrder = QSpinBox()
        self.filterCutoff = QSpinBox()
        _(QLabel("Filter Order"),0,0,1,1)
        _(self.filterOrder,0,1,1,1)
        _(QLabel("Cutoff Freq."),1,0,1,1)
        _(self.filterCutoff, 1,1,1,1)
        _(QLabel("nm<sup>-1</sup>"),1,2,1,1)
        self.layout.addWidget(self.signalPrep,2,0,1,2)
    
        '''Polynomial subtraction'''
        self.polySub = QGroupBox("Polynomial Subtraction")
        self.polySub.setFixedSize(150,100)
        self.polySub.setLayout(QGridLayout())
        _ = self.polySub.layout().addWidget
        self.polynomialOrder = QSpinBox()
        _(QLabel("Order"),0,0,1,1)
        _(self.polynomialOrder,0,1,1,1)
        self.layout.addWidget(self.polySub,2,2,1,2)
        
        '''Advanced Calculations'''
        self.advanced = CollapsibleSection('Skip Advanced Analysis', 100, self)
        self.advanced.stateChanged.connect(self.updateSize)
        layout = QGridLayout()
        _ = layout.addWidget
        _(QCheckBox("MinSub"))
        self.advanced.setLayout(layout)
        self.layout.addWidget(self.advanced,3,0,1,4)
        
    def loadFromSettings(self, settings:AnalysisSettings):
        self.filterOrder.setValue(settings.filterOrder)
        self.filterCutoff.setValue(settings.filterCutoff)
        self.polynomialOrder.setValue(settings.polynomialOrder)
        self.referenceMaterial.setValue(settings.referenceMaterial)
        
    def updateSize(self):
        height = 50 #give this much excess room.
        height += self.presets.height()
        height += self.hardwareCorrections.height()
        height += self.signalPrep.height()
        height += self.advanced.height()
        self.internalWidget.setFixedHeight(height)
        
class ResultsTableDock(QDockWidget):
    def __init__(self):
        super().__init__("Results")
        self.setObjectName('ResultsTableDock')
        columns = ('Cell#', "RMS", 'Reflectance', 'ld', 'etc.')
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.table = CopyableTable()
        self.table.setRowCount(5)
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.verticalHeader().hide()
        self.table.setItem(1,1,QTableWidgetItem("rms"))
        self.checkBoxes = QFrame()
        self.checkBoxes.setLayout(QVBoxLayout())
        for i,n in enumerate(columns):
            c = QCheckBox(n)
            c.setCheckState(2)
            f = lambda state,i=i : self.table.setColumnHidden(i,state==0)
            c.stateChanged.connect(f)
            self.checkBoxes.layout().addWidget(c)
        self.widget.layout().addWidget(self.checkBoxes)
        self.widget.layout().addWidget(self.table)
        self.setWidget(self.widget)
    def copy(self):
        for i in range(self.table.rowCount):
            for j in range(self.table.columnCount):
                if self.table.cellWidget(i,j).isSelected():
                    print('a')
        
        
class PlottingWidget(QDockWidget):
    def __init__(self, cellSelectorTable:CellTableWidget):
        super().__init__("Plotting")
        self.selector = cellSelectorTable
        self.setObjectName('PlottingWidget')
        self.plots = []
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        plotScroll = QScrollArea()
        plotScroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        plotScroll.setWidgetResizable(True)
        self.scrollContents = QWidget()
        self.arController = AspectRatioWidget(self.scrollContents, 1, self)
        self.scrollContents.setLayout(QVBoxLayout())
        plotScroll.setWidget(self.arController)
        buttons = QWidget()
        buttons.setLayout(QVBoxLayout())
        _ = buttons.layout().addWidget
        self.plotRMSButton = QPushButton("RMS")
        self.plotBFButton = QPushButton('BF')
        self.plot3dButton = QPushButton("3D")
        self.clearButton = QPushButton("Clear")
        self.plotRMSButton.released.connect(self.plotRMS)
        self.clearButton.released.connect(self.clearPlots)
        
        _(self.plotRMSButton)
        _(self.plotBFButton)
        _(self.plot3dButton)
        _(self.clearButton)
        self.widget.layout().addWidget(plotScroll)
        self.widget.layout().addWidget(buttons)
        self.setWidget(self.widget)
    
    def addPlot(self, plot):
        self.plots.append(plot)
        self.scrollContents.layout().addWidget(plot)
        self._plotsChanged()
        
    def clearPlots(self):
        for i in self.plots:
            self.scrollContents.layout().removeWidget(i)
            i.deleteLater()
            i=None   
        self.plots = []
        self._plotsChanged()
        
    def _plotsChanged(self):
        if len(self.plots)>0:
            self.arController.setAspect(1/len(self.plots))

    def plotRMS(self):  
        cells = self.selector.selectedCells
        if len(cells)==0:
            messageBox =  QMessageBox(self)
            messageBox.critical(self, "Oops!","Please select the cells you would like to plot.")
            messageBox.setFixedSize(500,200)
        for i in cells:      
            self.addPlot(LittlePlot())
        
