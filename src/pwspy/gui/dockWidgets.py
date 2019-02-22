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
                             QCheckBox, QSizePolicy, QSpacerItem, QMessageBox)
from PyQt5 import (QtCore, QtGui)
from customWidgets import CopyableTable, LittlePlot, CellTableWidget, CollapsibleSection, AspectRatioWidget, CellTableWidgetItem
from pwspy.analysis import AnalysisSettings
import os
from pwspy.imCube.ICMetaDataClass import ICMetaData


class CellSelectorDock(QDockWidget):
    def __init__(self):
        super().__init__("Cell Selector")
        self.setObjectName('CellSelectorDock') #needed for restore state to work
        self.tableWidget = CellTableWidget()
#        self.tableWidget.setRowCount(4)
#        self.tableWidget.setColumnCount(1)
#        self.tableWidget.setItem(0,0, QTableWidgetItem("Cell (1,1)"))
        self.setWidget(self.tableWidget)
        self.cells = []
    def addCell(self, fileName:str):
        self.cells.append(ICMetaData.loadAny(fileName))
        print(fileName)
        cell = CellTableWidgetItem(self.tableWidget, len(self.cells), self.cells[-1], int(os.path.split(fileName)[-1][4:]))
        
    
class AnalysisSettingsDock(QDockWidget):
    def __init__(self):
        super().__init__("Settings")
        self.setObjectName('AnalysisSettingsDock') #needed for restore state to work
        self.widget = QScrollArea()
        internalWidget = QFrame()
        internalWidget.setLayout(QVBoxLayout())
        internalWidget.setFixedSize(350,400)
#        internalWidget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        internalWidget2 = QFrame()
        internalWidget2.setMinimumSize(350,100)
        spacer = QSpacerItem(0,0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        internalWidget.layout().addWidget(internalWidget2)
        internalWidget.layout().addItem(spacer)
        self.widget.setWidget(internalWidget)
        self.layout = QGridLayout()#QVBoxLayout()
        internalWidget2.setLayout(self.layout)
        self.setupFrame()
        self.setWidget(self.widget)
        
    def setupFrame(self):
        '''Presets'''
        presets = QGroupBox("Presets")
#        presets.setFixedSize(300,50)
        presets.setLayout(QHBoxLayout())
        presets.layout().addWidget(QRadioButton("Legacy"))
        presets.layout().addWidget(QRadioButton("Reccommended"))
        self.layout.addWidget(presets,0,0,1,4)

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
        hardWareCorrections = CollapsibleSection('Automatic Correction',100,self)
        hardWareCorrections.setLayout(layout)

        self.layout.addWidget(hardWareCorrections,1,0,1,4)
        
        '''SignalPreparations'''
#        signalPrep = CollapsibleSection('Hey',2, self)
        signalPrep = QGroupBox("Signal Prep")
        signalPrep.setFixedSize(150,100)
        signalPrep.setLayout(QGridLayout())
        _ = signalPrep.layout().addWidget
        self.filterOrder = QSpinBox()
        self.filterCutoff = QSpinBox()
        _(QLabel("Filter Order"),0,0,1,1)
        _(self.filterOrder,0,1,1,1)
        _(QLabel("Cutoff Freq."),1,0,1,1)
        _(self.filterCutoff, 1,1,1,1)
        _(QLabel("nm<sup>-1</sup>"),1,2,1,1)
        self.layout.addWidget(signalPrep,2,0,1,2)
    
        '''Polynomial subtraction'''
        polySub = QGroupBox("Polynomial Subtraction")
        polySub.setFixedSize(150,100)
        polySub.setLayout(QGridLayout())
        _ = polySub.layout().addWidget
        self.polynomialOrder = QSpinBox()
        _(QLabel("Order"),0,0,1,1)
        _(self.polynomialOrder,0,1,1,1)
        self.layout.addWidget(polySub,2,2,1,2)
#        sublayout = QHBoxLayout()
#        sublayout.addWidget(signalPrep)
#        sublayout.addWidget(polySub)
#        _ = QWidget()
#        _.setLayout(sublayout)
#        self.layout.addWidget(_)
        
        '''Advanced Calculations'''
        advanced = CollapsibleSection('Skip Advanced Analysis', 100, self)
        layout = QGridLayout()
        _ = layout.addWidget
        _(QCheckBox("MinSub"))
        advanced.setLayout(layout)
        self.layout.addWidget(advanced,3,0,1,4)
        
    def loadFromSettings(self, settings:AnalysisSettings):
        self.filterOrder.setValue(settings.filterOrder)
        self.filterCutoff.setValue(settings.filterCutoff)
        self.polynomialOrder.setValue(settings.polynomialOrder)
        self.referenceMaterial.setValue(settings.referenceMaterial)
        
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
        for i in range(4):
            self.addPlot(LittlePlot())
#        scrollContents.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
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
        
