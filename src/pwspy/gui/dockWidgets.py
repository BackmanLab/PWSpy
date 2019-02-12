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
                             QCheckBox)
from PyQt5 import (QtCore, QtGui)
from customWidgets import CopyableTable, LittlePlot


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
        self.signalPrep()
        self.polySub()
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
        frame.layout().addWidget(QLabel("R Subtraction"))
        frame.layout().addWidget(QLineEdit())
        frame.layout().addWidget(QPushButton())
        _(frame,1,0,1,4)
        self.layout.addWidget(self.hardWareCorrections,1,0,2,2)
        
    def signalPrep(self):
        self.signalPrep = QGroupBox("Signal Prep")
        self.signalPrep.setLayout(QGridLayout())
        _ = self.signalPrep.layout().addWidget
        _(QLabel("Filter Order"),0,0,1,1)
        _(QSpinBox(),0,1,1,1)
        _(QLabel("Cutoff Freq."),1,0,1,1)
        _(QSpinBox(),1,1,1,1)
        _(QLabel("{Freq units here}"),1,2,1,1)
        self.layout.addWidget(self.signalPrep)
    
    def polySub(self):
        self.polySub = QGroupBox("Polynomial Subtraction")
        self.polySub.setLayout(QGridLayout())
        _ = self.polySub.layout().addWidget
        _(QLabel("Order"),0,0,1,1)
        _(QSpinBox(),0,1,1,1)
        self.layout.addWidget(self.polySub)
        
class ResultsTable(QDockWidget):
    def __init__(self):
        super().__init__("Results")
        columns = ("RMS", 'ld', 'Cell', 'etc')
        self.widget = QWidget()
        self.widget.setLayout(QHBoxLayout())
        self.table = CopyableTable()
        self.table.setRowCount(5)
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
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
        
