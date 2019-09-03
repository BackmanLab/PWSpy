import os

import numpy as np
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QMenu, QAction
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pwspy.analysis import AnalysisResultsLoader
from .widgets import AnalysisPlotter
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.analysisViewer import AnalysisViewer
from pwspy.dataTypes import ImCube, ICMetaData
from pwspy.utility import PlotNd


class LittlePlot(FigureCanvasQTAgg, AnalysisPlotter):
    def __init__(self, metadata: ICMetaData, analysis: AnalysisResultsLoader, title: str, text: str = None, initialField='thumbnail'):
        AnalysisPlotter.__init__(self, metadata, analysis)
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.im = self.ax.imshow(np.zeros((100, 100)), cmap='gray')
        self.title = title
        self.ax.set_title(self.title, fontsize=8)
        self.ax.yaxis.set_visible(False)
        self.ax.xaxis.set_visible(False)
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.mpl_connect("button_release_event", self.mouseReleaseEvent)
        self.setMinimumWidth(20)
        self.changeData(initialField)
        if text is not None:
            self.ax.text(1, 50, text)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.plotnd = None #Just a reference to a plotND class instance so it isn't deleted.

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            AnalysisViewer(metadata=self.metadata, analysisLoader=self.analysis, title=self.title, parent=self, initialField=self.analysisField)

    def changeData(self, field):
        AnalysisPlotter.changeData(self, field)
        self.im.set_data(self.data)
        self.im.set_clim((np.percentile(self.data, 0.1), np.percentile(self.data, 99.9)))
        self.draw_idle()

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        if self.analysis is not None:
            anPlotAction = QAction("Plot3d Analyzed Reflectance", self)
            anPlotAction.triggered.connect(self.plotAn3d)
            menu.addAction(anPlotAction)
            if 'reflectance' in self.analysis.file.keys():
                opdAction = QAction("Plot3d OPD", self)
                opdAction.triggered.connect(self.plotOpd3d)
                menu.addAction(opdAction)
        rawPlotAction = QAction("Plot3d Raw Data", self)
        rawPlotAction.triggered.connect(self.plotRaw3d)
        menu.addAction(rawPlotAction)
        menu.exec(self.mapToGlobal(point))

    def plotAn3d(self):
        self.plotnd = PlotNd(self.analysis.reflectance.data, title=os.path.split(self.metadata.filePath)[-1],
                             names=('y', 'x', 'k'), extraDimIndices=[self.analysis.reflectance.wavenumbers])

    def plotRaw3d(self):
        im = ImCube.fromMetadata(self.metadata)
        self.plotnd = PlotNd(im.data, title=os.path.split(self.metadata.filePath)[-1],
                             extraDimIndices=[im.wavelengths])

    def plotOpd3d(self):
        opd, opdIndex = self.analysis.opd
        self.plotnd = PlotNd(opd, names=('y', 'x', '(um)'), title=os.path.split(self.metadata.filePath)[-1],
                             extraDimIndices=[opdIndex])
