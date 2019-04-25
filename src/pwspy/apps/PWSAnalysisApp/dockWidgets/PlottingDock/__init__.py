from typing import List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QScrollArea, QVBoxLayout, QPushButton, QMessageBox, \
    QComboBox, QLabel

from pwspy.apps.PWSAnalysisApp.dockWidgets import CellSelectorDock
from pwspy.imCube.ICMetaDataClass import ICMetaData
from .widgets import AspectRatioWidget, LittlePlot
import os
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
        self.scrollContents = QWidget()
        self.arController = AspectRatioWidget(self.scrollContents, 1, self)
        self.scrollContents.setLayout(QVBoxLayout())
        plotScroll.setWidget(self.arController)
        buttons = QWidget()
        buttons.setLayout(QVBoxLayout())
        _ = buttons.layout().addWidget
        self.anNameComboBox = QComboBox(self)
        self.updateAnalysisNames()
        self.plotRMSButton = QPushButton("RMS")
        self.plotBFButton = QPushButton('BF')
        self.plot3dButton = QPushButton("3D")
        self.clearButton = QPushButton("Clear")
        self.plotRMSButton.released.connect(self.plotRMS)
        self.clearButton.released.connect(self.clearPlots)

        _(QLabel("Analysis Name"))
        _(self.anNameComboBox)
        _(self.plotRMSButton)
        _(self.plotBFButton)
        _(self.plot3dButton)
        _(self.clearButton)
        self._widget.layout().addWidget(plotScroll)
        self._widget.layout().addWidget(buttons)
        self.setWidget(self._widget)

    def updateAnalysisNames(self):
        self.anNameComboBox.clear()
        self.anNameComboBox.addItems([])  # TODO determine which analyses are present

    def addPlot(self, plot):
        self.plots.append(plot)
        self.scrollContents.layout().addWidget(plot)
        self._plotsChanged()

    def clearPlots(self):
        for i in self.plots:
            self.scrollContents.layout().removeWidget(i)
            i.deleteLater()
            i = None
        self.plots = []
        self._plotsChanged()

    def _plotsChanged(self):
        if len(self.plots) > 0:
            self.arController.aspect = 1 / len(self.plots)

    def plotRMS(self):
        analysisName = self.anNameComboBox.currentText()
        cells: List[ICMetaData] = self.selector.getSelectedCellMetas()
        if len(cells) == 0:
            messageBox = QMessageBox(self)
            messageBox.information(self, "Oops!", "Please select the cells you would like to plot.")
            messageBox.setFixedSize(500, 200)
        for cell in cells:
            try:
                if analysisName in cell.getAnalyses():
                    self.addPlot(LittlePlot(cell.loadAnalysis(analysisName).rms, cell))
                else:
                    print(f'{os.path.split(cell.filePath)[-1]} does not have a "{analysisName}" analysis.')
            except KeyError:
                print(f'{os.path.split(cell.filePath)[-1]} does not have an RMS field for analysis "{analysisName}"')
