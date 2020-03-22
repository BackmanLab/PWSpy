import traceback
from typing import List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QScrollArea, QVBoxLayout, QPushButton, QMessageBox, \
    QLabel, QLineEdit, QSizePolicy, QButtonGroup, QFrame

from pwspy.apps.PWSAnalysisApp._dockWidgets import CellSelectorDock
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.roiDrawer import RoiDrawer
from pwspy.dataTypes import ICMetaData
from pwspy.dataTypes.metadata import AcqDir
from pwspy.apps.sharedWidgets.utilityWidgets import AspectRatioWidget
from pwspy.utility.misc import profileDec
from .widgets.littlePlot import LittlePlot
import os

from ..._utilities.conglomeratedAnalysis import ConglomerateAnalysisResults


class PlottingDock(QDockWidget):
    def __init__(self, selector: CellSelectorDock):
        super().__init__("Plotting")
        self.selector = selector
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.roiDrawer = None
        self.setObjectName('PlottingWidget')
        self.plots = []
        self.cellMetas = []
        self._widget = QWidget()
        self._widget.setLayout(QHBoxLayout())
        self.plotScroll = QScrollArea()
        self.plotScroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self.plotScroll.setWidgetResizable(True)
        self.plotScroll.horizontalScrollBar().setEnabled(False)
        self.plotScroll.horizontalScrollBar().setVisible(False)
        self.plotScroll.setMinimumWidth(75)
        self.plotScroll.setMaximumWidth(600)
        self.scrollContents = AspectRatioWidget(1, self)
        self.scrollContents.setLayout(QVBoxLayout())
        a = QSizePolicy()
        # a.setHeightForWidth(True)
        a.setHorizontalPolicy(QSizePolicy.Maximum) #Stretch out as much as possible horizontally
        self.scrollContents.setSizePolicy(a)

        self.plotScroll.setWidget(self.scrollContents)
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
        self.plotThumbnailButton = QPushButton("Thumbnail")
        self.plotRMSButton = QPushButton("RMS")
        self.plotRButton = QPushButton('R')
        self.buttonGroup.addButton(self.plotThumbnailButton)
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
        self.refreshButton.released.connect(lambda: self.generatePlots(self.selector.getSelectedCellMetas()))
        self.roiButton = QPushButton("Draw Roi's")
        self.roiButton.released.connect(self.startRoiDrawing)
        label = QLabel("Analysis Name")
        label.setMaximumHeight(20)
        _(label)
        _(self.anNameEdit)
        _(self.refreshButton)
        _(self.roiButton)
        _(frame)

        self._widget.layout().addWidget(self.plotScroll)
        self._widget.layout().addWidget(buttons)
        # self._widget.setMaximumWidth(self.plotScroll.maximumWidth()+buttons.maximumWidth()+10)
        self.setWidget(self._widget)

        self.enableAnalysisPlottingButtons('false')

    def addPlot(self, plot: QWidget):
        self.plots.append(plot)
        self.scrollContents.layout().addWidget(plot)
        self._plotsChanged()

    def addPlots(self, plots: List[QWidget]):
        self.plots.extend(plots)
        [self.scrollContents.layout().addWidget(plot) for plot in plots]
        self._plotsChanged()

    def _plotsChanged(self):
        if len(self.plots) > 0:
            self.scrollContents.setAspect(1 / len(self.plots))

    def startRoiDrawing(self):
        metadatas = [(p.acq, p.analysis) for p in self.plots]
        if len(metadatas) > 0: # Otherwise we crash
            self.roiDrawer = RoiDrawer(metadatas)
        else:
            QMessageBox.information(self, "Oops", "Please select which cells to plot.")

    def anNameEditFinished(self):
        #Sometimes the signal gets sent twice. only generate plots if the string has changed.
        pattern = self.anNameEdit.text()
        if pattern != self._oldPattern or self.cellMetas != self._oldCells:
            # Determine if a name has been entered
            # if self.anNameEdit.text().strip() == '':
            #     self.enableAnalysisPlottingButtons(False)
            # else:
            #     self.enableAnalysisPlottingButtons(True)
            self.generatePlots(self.selector.getSelectedCellMetas())
        self._oldPattern = pattern
        self._oldCells = self.cellMetas

    def enableAnalysisPlottingButtons(self, enable: str):
        enable = enable.lower()
        if enable == 'false':
            for button in self.buttonGroup.buttons():
                button.setEnabled(False)
            self.roiButton.setEnabled(False)
        elif enable == 'partial':
            for button in self.buttonGroup.buttons():
                if not button is self.plotThumbnailButton:
                    button.setEnabled(False)
            self.plotThumbnailButton.setEnabled(True)
            self.roiButton.setEnabled(True)
        elif enable == 'true':
            for button in self.buttonGroup.buttons():
                if not button is self.plotThumbnailButton:
                    button.setEnabled(True)
            self.plotThumbnailButton.setEnabled(True)
            self.roiButton.setEnabled(True)
        else:
            raise ValueError("`enable` string not recognized.")

    def generatePlots(self, cells: List[AcqDir]):
        try:
            self.cellMetas = cells
            analysisName = self.anNameEdit.text()
            #clear Plots
            for i in self.plots:
                self.scrollContents.layout().removeWidget(i)
                i.deleteLater()
            self.plots = []
            if len(self.cellMetas) == 0:
                messageBox = QMessageBox(self)
                messageBox.information(self, "Oops!", "Please select the cells you would like to plot.")
                messageBox.setFixedSize(500, 200)
            buttonState = 'false'
            plotsToAdd = []
            for cell in cells:
                if analysisName.strip() == '': #No analysis name was entered. don't load an analysis, just the thumbnail
                    plotsToAdd.append(LittlePlot(cell, ConglomerateAnalysisResults(None, None), f"{os.path.split(cell.filePath)[-1]}"))
                    buttonState = 'partial'
                else:
                    dynAnalysis = pwsAnalysis = None
                    if cell.pws is not None:
                        if analysisName in cell.pws.getAnalyses():
                            pwsAnalysis = cell.pws.loadAnalysis(analysisName)
                    if cell.dynamics is not None:
                        if analysisName in cell.dynamics.getAnalyses():
                            dynAnalysis = cell.dynamics.loadAnalysis(analysisName)
                    analysis = ConglomerateAnalysisResults(pwsAnalysis, dynAnalysis)
                    if pwsAnalysis is None and dynAnalysis is None: #Specified analysis was not found, load a dummy widget
                        plotsToAdd.append(LittlePlot(cell, ConglomerateAnalysisResults(None, None), f"{analysisName} {os.path.split(cell.filePath)[-1]}", "Analysis Not Found!"))
                    else:
                        plotsToAdd.append(LittlePlot(cell, analysis, f"{analysisName} {os.path.split(cell.filePath)[-1]}"))
                        buttonState = 'true'
            self.addPlots(plotsToAdd)
            self.enableAnalysisPlottingButtons(buttonState)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.information(self, "Error!", str(e))

    def handleButtons(self, button: QPushButton):
        if button != self._lastButton:
            for plot in self.plots:
                try:
                    if button is self.plotThumbnailButton:
                        plot.changeData(plot.PlotFields.Thumbnail)
                    elif button is self.plotRMSButton:
                        plot.changeData(plot.PlotFields.RMS)
                    elif button is self.plotRButton:
                        plot.changeData(plot.PlotFields.MeanReflectance)
                except ValueError:  # The analysis field wasn't found
                    plot.changeData(plot.PlotFields.Thumbnail)
            self._lastButton = button
