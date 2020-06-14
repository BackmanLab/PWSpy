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

import os

import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QMenu, QAction, QWidget, QLabel, QVBoxLayout
from pwspy.apps.PWSAnalysisApp.utilities.conglomeratedAnalysis import ConglomerateAnalysisResults
from pwspy.dataTypes import AcqDir, ImCube
from .widgets import AnalysisPlotter
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.analysisViewer import AnalysisViewer
from pwspy.utility.plotting import PlotNd


class LittlePlot(AnalysisPlotter, QWidget):
    def __init__(self, acquisition: AcqDir, analysis: ConglomerateAnalysisResults, title: str, text: str = None,
                 initialField=AnalysisPlotter.PlotFields.Thumbnail):
        assert analysis is not None #The member of the conglomerateAnalysisResults can be None but the way this class is written requires that the object itself exists.
        AnalysisPlotter.__init__(self, acquisition, analysis)
        QWidget.__init__(self)
        self.setLayout(QVBoxLayout())
        self.titleLabel = QLabel(title, self)
        self.titleLabel.setAlignment(QtCore.Qt.AlignCenter)
        self.imLabel = QLabel(self)
        self.imLabel.setScaledContents(True)
        self.layout().addWidget(self.titleLabel)
        if text is not None:
            self.textLabel = QLabel(self)
            self.textLabel.setStyleSheet("QLabel {color: #b40000}") #This isn't working for some reason
            self.textLabel.setText(text)
            self.textLabel.setAlignment(QtCore.Qt.AlignCenter)
            self.layout().addWidget(self.textLabel)
        self.layout().addWidget(self.imLabel)
        self.title = title
        self.setMinimumWidth(20)
        self.changeData(initialField)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.plotnd = None #Just a reference to a plotND class instance so it isn't deleted.

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            AnalysisViewer(metadata=self.acq, analysisLoader=self.analysis, title=self.title, parent=self, initialField=self.analysisField)

    def changeData(self, field: AnalysisPlotter.PlotFields):
        AnalysisPlotter.changeData(self, field)
        data = self.data
        data = data - np.percentile(data, 0.1)
        data = (data / np.percentile(data, 99.9) * 255)
        data[data<0] = 0
        data[data>255] = 255
        data = data.astype(np.uint8)
        p = QPixmap.fromImage(QImage(data.data, data.shape[1], data.shape[0], data.strides[0], QImage.Format_Grayscale8))
        self.imLabel.setPixmap(p)

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        if self.analysis.pws is not None:
            anPlotAction = QAction("Plot PWS Analyzed Reflectance", self)
            anPlotAction.triggered.connect(self.plotAn3d)
            menu.addAction(anPlotAction)
            if 'reflectance' in self.analysis.pws.file.keys():
                opdAction = QAction("Plot OPD", self)
                opdAction.triggered.connect(self.plotOpd3d)
                menu.addAction(opdAction)
        if self.acq.pws is not None:
            rawPlotAction = QAction("Plot PWS Raw Data", self)
            rawPlotAction.triggered.connect(self.plotRaw3d)
            menu.addAction(rawPlotAction)
        if self.analysis.dyn is not None:
            dynAnPlotAction = QAction("Plot DYN Analyzed Reflectance", self)
            dynAnPlotAction.triggered.connect(self.plotDynAn3d)
            menu.addAction(dynAnPlotAction)
        if self.acq.dynamics is not None:
            dynRawPlotAction = QAction("Plot DYN Raw Data", self)
            dynRawPlotAction.triggered.connect(self.plotDynRaw3d)
            menu.addAction(dynRawPlotAction)
        menu.exec(self.mapToGlobal(point))

    def plotAn3d(self):
        refl = self.analysis.pws.reflectance
        self.plotnd = PlotNd(refl.data, title=os.path.split(self.acq.filePath)[-1], names=('y', 'x', 'k (rad/um)'),
                             indices=[range(refl.data.shape[0]), range(refl.data.shape[1]), refl.wavenumbers])

    def plotRaw3d(self):
        im = ImCube.fromMetadata(self.acq.pws)
        self.plotnd = PlotNd(im.data, title=os.path.split(self.acq.filePath)[-1], names=('y', 'x', 'lambda'),
                             indices=[range(im.data.shape[0]), range(im.data.shape[1]), im.wavelengths])

    def plotOpd3d(self):
        opd, opdIndex = self.analysis.pws.opd
        self.plotnd = PlotNd(opd, names=('y', 'x', 'um'), title=os.path.split(self.acq.filePath)[-1],
                             indices=[range(opd.shape[0]), range(opd.shape[1]), opdIndex])

    def plotDynAn3d(self):
        refl = self.analysis.dyn.reflectance
        self.plotnd = PlotNd(refl.data, title=os.path.split(self.acq.filePath)[-1],
                             names=('y', 'x', 't'),
                             indices=[range(refl.data.shape[0]), range(refl.data.shape[1]), refl.times])

    def plotDynRaw3d(self):
        im = self.acq.dynamics.toDataClass()
        self.plotnd = PlotNd(im.data, title=os.path.split(self.acq.filePath)[-1], names=('y', 'x', 't'),
                             indices=[range(im.data.shape[0]), range(im.data.shape[1]), im.times])