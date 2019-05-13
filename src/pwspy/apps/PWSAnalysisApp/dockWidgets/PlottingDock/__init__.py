from typing import List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QScrollArea, QVBoxLayout, QPushButton, QMessageBox, \
    QComboBox, QLabel, QLineEdit, QSizePolicy, QButtonGroup, QFrame

from pwspy.apps.PWSAnalysisApp.dockWidgets import CellSelectorDock
from pwspy.apps.PWSAnalysisApp.dockWidgets.PlottingDock.widgets import RoiDrawer
from pwspy.imCube.ICMetaDataClass import ICMetaData
from .widgets import AspectRatioWidget, LittlePlot
import os
import re
# TODO add blinded roi drawing

class PlottingDock(QDockWidget):
    def __init__(self, cellSelectorTable: CellSelectorDock):
        super().__init__("Plotting")
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.selector = cellSelectorTable
        self.setObjectName('PlottingWidget')
        self.plots = []
        self._widget = QWidget()
        self._widget.setLayout(QHBoxLayout())
        plotScroll = QScrollArea()
        plotScroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        plotScroll.setWidgetResizable(True)
        plotScroll.horizontalScrollBar().setEnabled(False)
        plotScroll.horizontalScrollBar().setVisible(False)
        self.scrollContents = AspectRatioWidget(1, self)
        self.scrollContents.setLayout(QVBoxLayout())
        a = QSizePolicy()
        a.setHeightForWidth(True)
        a.setHorizontalPolicy(QSizePolicy.Maximum)
        self.scrollContents.setSizePolicy(a)

        plotScroll.setWidget(self.scrollContents)
        buttons = QWidget()
        buttons.setMaximumWidth(100)
        buttons.setLayout(QVBoxLayout())
        _ = buttons.layout().addWidget
        self.anNameEdit = QLineEdit(self)
        self._oldPattern = ''
        self._oldCells = None
        self.anNameEdit.editingFinished.connect(self.anNameEditFinished)
        self.buttonGroup = QButtonGroup()
        self._lastButton = None
        self.buttonGroup.buttonReleased.connect(self.handleButtons)
        self.plotImBdButton = QPushButton("ImBd")
        self.plotRMSButton = QPushButton("RMS")
        self.plotRButton = QPushButton('R')
        self.buttonGroup.addButton(self.plotImBdButton)
        self.buttonGroup.addButton(self.plotRMSButton)
        self.buttonGroup.addButton(self.plotRButton)
        [i.setCheckable(True) for i in self.buttonGroup.buttons()]
        self.buttonGroup.buttons()[0].setChecked(True)
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        l = QVBoxLayout()
        [l.addWidget(i) for i in self.buttonGroup.buttons()]
        frame.setLayout(l)
        self.refreshButton = QPushButton("Refresh")
        self.refreshButton.released.connect(self.generatePlots)
        self.roiButton = QPushButton("Draw Roi's")
        self.roiButton.released.connect(self.startRoiDrawing)
        label = QLabel("Analysis Name")
        label.setMaximumHeight(20)
        _(label)
        _(self.anNameEdit)
        _(self.refreshButton)
        _(self.roiButton)
        _(frame)


        self._widget.layout().addWidget(plotScroll)
        self._widget.layout().addWidget(buttons)
        self.setWidget(self._widget)

    def addPlot(self, plot):
        self.plots.append(plot)
        self.scrollContents.layout().addWidget(plot)
        self._plotsChanged()

    def _plotsChanged(self):
        if len(self.plots) > 0:
            self.scrollContents.setAspect(1 / len(self.plots))

    def startRoiDrawing(self):
        RoiDrawer(self.plots[0].analysis, self.plots[0].metadata) #This is just placeholder

    def anNameEditFinished(self):
        #Sometimes the signal gets sent twice. only generate plots if the string has changed.
        pattern = self.anNameEdit.text()
        cells = self.selector.getSelectedCellMetas()
        if pattern != self._oldPattern or cells != self._oldCells:
            self.generatePlots()
        self._oldPattern = pattern
        self._oldCells = cells

    def generatePlots(self):
        #clear Plots
        for i in self.plots:
            self.scrollContents.layout().removeWidget(i)
            i.deleteLater()
            i = None
        self.plots = []
        analysisNamePattern = self.anNameEdit.text()
        cells: List[ICMetaData] = self.selector.getSelectedCellMetas()
        if len(cells) == 0:
            messageBox = QMessageBox(self)
            messageBox.information(self, "Oops!", "Please select the cells you would like to plot.")
            messageBox.setFixedSize(500, 200)
        for cell in cells:
            if analysisNamePattern.strip() == '': #No analysis name was entered. don't load an analysis
                self.addPlot(LittlePlot(cell, None, f"{os.path.split(cell.filePath)[-1]}"))
            else:
                for anName in cell.getAnalyses():
                    try:
                        if re.fullmatch(analysisNamePattern, anName):
                            analysis = cell.loadAnalysis(anName)
                            self.addPlot(LittlePlot(cell, analysis, f"{anName} {os.path.split(cell.filePath)[-1]}"))
                    except re.error as e:
                        print(e)
        self._plotsChanged()

    def handleButtons(self, button: QPushButton):
        if button != self._lastButton:
            for plot in self.plots: #TODO handle errors for missing analyses.
                try:
                    if button is self.plotImBdButton:
                        plot.changeData('imbd')
                    elif button is self.plotRMSButton:
                        plot.changeData('rms')
                    elif button is self.plotRButton:
                        plot.changeData('meanReflectance')
                except ValueError: #The analysis field wasn't found
                    plot.changeData('imbd')
            self._lastButton = button
