# -*- coding: utf-8 -*-
"""
Created on Wed Feb 13 18:04:57 2019

@author: backman05
"""
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QDockWidget
from PyQt5.QtWidgets import (QTableWidget,QTableWidgetItem, QVBoxLayout,
                             QTabWidget, QTextEdit, QLabel, QGroupBox,
                             QGridLayout, QApplication, QStyleFactory, QDialog,
                             QHBoxLayout, QLineEdit, QPushButton, QFileDialog)
import os

class WorkingDirDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Working Directory")
        self.setLayout(QGridLayout())
        self.textLine = QLineEdit()
        self.browseButton = QPushButton(QtGui.QIcon(os.path.join('resources','folder.png')),'')
        self.okButton = QPushButton('OK')
        self.layout().addWidget(self.textLine,0,0,1,4)
        self.layout().addWidget(self.browseButton,0,5,1,1)
        self.layout().addWidget(self.okButton,1,2,1,1)
        self.setFixedSize(400,75)
        self.okButtonPushed = QtCore.pyqtSignal(str)
        self.okButton.released.connect(self.okButtonPushed_)
        self.browseButton.released.connect(self.browseFile)
        
    def okButtonPushed_(self):
        self.accept()
        self.okButtonPushed.emit( self.textLine.text)
        
    def browseFile(self):
        _ = QFileDialog(self)
        _.setFileMode(QFileDialog.DirectoryOnly)
        _.show()
        _.fileSelected.connect(self.textLine.setText)