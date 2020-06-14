# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

import logging
import traceback
from typing import List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QDockWidget, QWidget, QHBoxLayout, QScrollArea, QVBoxLayout, QPushButton, QMessageBox, \
    QLabel, QLineEdit, QSizePolicy, QButtonGroup, QFrame

from pwspy.apps.PWSAnalysisApp._dockWidgets import CellSelectorDock
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.roiDrawer import RoiDrawer
import pwspy.dataTypes as pwsdt
from pwspy.apps.sharedWidgets.utilityWidgets import AspectRatioWidget
from .widgets.littlePlot import LittlePlot
import os

from ...utilities.conglomeratedAnalysis import ConglomerateAnalysisResults
from ...componentInterfaces import CellSelector


class PlottingDock(QDockWidget):
    def __init__(self, selector: CellSelector):
        super().__init__("Plotting")
        self.selector = selector
        self.setStyleSheet("QDockWidget > QWidget { border: 1px solid lightgray; }")
        self.roiDrawer = None
        self.setObjectName('PlottingWidget')
        self._plots = []
        self.cellMetas = []
        self._widget = QWidget()
        self._widget.setLayout(QHBoxLayout())
        self._plotScroll = QScrollArea()
        self._plotScroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOn)
        self._plotScroll.setWidgetResizable(True)
        self._plotScroll.horizontalScrollBar().setEnabled(False)
        self._plotScroll.horizontalScrollBar().setVisible(False)
        self._plotScroll.setMinimumWidth(75)
        self._plotScroll.setMaximumWidth(600)
        self._scrollContents = AspectRatioWidget(1, self)
        self._scrollContents.setLayout(QVBoxLayout())
        a = QSizePolicy()
        # a.setHeightForWidth(True)
        a.setHorizontalPolicy(QSizePolicy.Maximum) #Stretch out as much as possible horizontally
        self._scrollContents.setSizePolicy(a)

        self._plotScroll.setWidget(self._scrollContents)
        buttons = QWidget()
        buttons.setMaximumWidth(100)
        buttons.setLayout(QVBoxLayout())
        _ = buttons.layout().addWidget
        self._anNameEdit = QLineEdit(self)
        self._oldPattern = ''
        self._oldCells = None
        self._anNameEdit.editingFinished.connect(self._anNameEditFinished)
        self._buttonGroup = QButtonGroup()
        self._lastButton = None
        self._buttonGroup.buttonReleased.connect(self._handleButtons)
        self._plotThumbnailButton = QPushButton("Thumbnail")
        self._plotRMSButton = QPushButton("RMS")
        self._plotRButton = QPushButton('R')
        self._buttonGroup.addButton(self._plotThumbnailButton)
        self._buttonGroup.addButton(self._plotRMSButton)
        self._buttonGroup.addButton(self._plotRButton)
        [i.setCheckable(True) for i in self._buttonGroup.buttons()]
        self._buttonGroup.buttons()[0].setChecked(True)
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel | QFrame.Plain)
        l = QVBoxLayout()
        [l.addWidget(i) for i in self._buttonGroup.buttons()]
        frame.setLayout(l)
        self._refreshButton = QPushButton("Refresh")
        self._refreshButton.released.connect(lambda: self._generatePlots(self.selector.getSelectedCellMetas()))
        self._roiButton = QPushButton("Draw Roi's")
        self._roiButton.released.connect(self._startRoiDrawing)
        label = QLabel("Analysis Name")
        label.setMaximumHeight(20)
        _(label)
        _(self._anNameEdit)
        _(self._refreshButton)
        _(self._roiButton)
        _(frame)

        self._widget.layout().addWidget(self._plotScroll)
        self._widget.layout().addWidget(buttons)
        # self._widget.setMaximumWidth(self.plotScroll.maximumWidth()+buttons.maximumWidth()+10)
        self.setWidget(self._widget)

        self._enableAnalysisPlottingButtons('false')

    def addPlot(self, plot: QWidget):
        self._plots.append(plot)
        self._scrollContents.layout().addWidget(plot)
        self._plotsChanged()

    def addPlots(self, plots: List[QWidget]):
        self._plots.extend(plots)
        [self._scrollContents.layout().addWidget(plot) for plot in plots]
        self._plotsChanged()

    def _plotsChanged(self):
        if len(self._plots) > 0:
            self._scrollContents.setAspect(1 / len(self._plots))

    def _startRoiDrawing(self):
        metadatas = [(p.acq, p.analysis) for p in self._plots]
        if len(metadatas) > 0: # Otherwise we crash
            self.roiDrawer = RoiDrawer(metadatas)
        else:
            QMessageBox.information(self, "Oops", "Please select which cells to plot.")

    def _anNameEditFinished(self):
        #Sometimes the signal gets sent twice. only generate plots if the string has changed.
        pattern = self._anNameEdit.text()
        if pattern != self._oldPattern or self.cellMetas != self._oldCells:
            # Determine if a name has been entered
            # if self.anNameEdit.text().strip() == '':
            #     self.enableAnalysisPlottingButtons(False)
            # else:
            #     self.enableAnalysisPlottingButtons(True)
            self._generatePlots(self.selector.getSelectedCellMetas())
        self._oldPattern = pattern
        self._oldCells = self.cellMetas

    def _enableAnalysisPlottingButtons(self, enable: str):
        enable = enable.lower()
        if enable == 'false':
            for button in self._buttonGroup.buttons():
                button.setEnabled(False)
            self._roiButton.setEnabled(False)
        elif enable == 'partial':
            for button in self._buttonGroup.buttons():
                if not button is self._plotThumbnailButton:
                    button.setEnabled(False)
            self._plotThumbnailButton.setEnabled(True)
            self._roiButton.setEnabled(True)
        elif enable == 'true':
            for button in self._buttonGroup.buttons():
                if not button is self._plotThumbnailButton:
                    button.setEnabled(True)
            self._plotThumbnailButton.setEnabled(True)
            self._roiButton.setEnabled(True)
        else:
            raise ValueError("`enable` string not recognized.")

    def _generatePlots(self, cells: List[pwsdt.AcqDir]):
        try:
            self.cellMetas = cells
            analysisName = self._anNameEdit.text()
            #clear Plots
            for i in self._plots:
                self._scrollContents.layout().removeWidget(i)
                i.deleteLater()
            self._plots = []
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
            self._enableAnalysisPlottingButtons(buttonState)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(e)
            QMessageBox.information(self, "Error!", str(e))

    def _handleButtons(self, button: QPushButton):
        if button != self._lastButton:
            for plot in self._plots:
                try:
                    if button is self._plotThumbnailButton:
                        plot.changeData(plot.PlotFields.Thumbnail)
                    elif button is self._plotRMSButton:
                        plot.changeData(plot.PlotFields.RMS)
                    elif button is self._plotRButton:
                        plot.changeData(plot.PlotFields.MeanReflectance)
                except ValueError:  # The analysis field wasn't found
                    plot.changeData(plot.PlotFields.Thumbnail)
            self._lastButton = button
