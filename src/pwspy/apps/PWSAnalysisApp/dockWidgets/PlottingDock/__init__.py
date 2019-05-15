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
        self.roiDrawer = None
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
        self.refreshButton.released.connect(lambda: self.generatePlots(self.anNameEdit.text()))
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
        self.generatePlots(self.anNameEdit.text())
        metadatas = [(p.metadata, p.analysis) for p in self.plots]
        if len(metadatas) > 0: # Otherwise we crash
            self.roiDrawer = RoiDrawer(metadatas)
        else:
            QMessageBox.information(self, "Oops", "Please select which cells to plot.")

    def anNameEditFinished(self):
        #Sometimes the signal gets sent twice. only generate plots if the string has changed.
        pattern = self.anNameEdit.text()
        cells = self.selector.getSelectedCellMetas()
        if pattern != self._oldPattern or cells != self._oldCells:
            self.generatePlots(pattern)
        self._oldPattern = pattern
        self._oldCells = cells

    def generatePlots(self, analysisName: str):
        #clear Plots
        for i in self.plots:
            self.scrollContents.layout().removeWidget(i)
            i.deleteLater()
        self.plots = []
        cells: List[ICMetaData] = self.selector.getSelectedCellMetas()
        if len(cells) == 0:
            messageBox = QMessageBox(self)
            messageBox.information(self, "Oops!", "Please select the cells you would like to plot.")
            messageBox.setFixedSize(500, 200)
        for cell in cells:
            if analysisName.strip() == '': #No analysis name was entered. don't load an analysis
                self.addPlot(LittlePlot(cell, None, f"{os.path.split(cell.filePath)[-1]}"))
            else:
                if analysisName in cell.getAnalyses():
                    analysis = cell.loadAnalysis(analysisName)
                    self.addPlot(LittlePlot(cell, analysis, f"{analysisName} {os.path.split(cell.filePath)[-1]}"))
        self._plotsChanged()

    def handleButtons(self, button: QPushButton):
        if button != self._lastButton:
            for plot in self.plots:
                try:
                    if button is self.plotImBdButton:
                        plot.changeData('imbd')
                    elif button is self.plotRMSButton:
                        plot.changeData('rms')
                    elif button is self.plotRButton:
                        plot.changeData('meanReflectance')
                except ValueError:  # The analysis field wasn't found
                    plot.changeData('imbd')
            self._lastButton = button
