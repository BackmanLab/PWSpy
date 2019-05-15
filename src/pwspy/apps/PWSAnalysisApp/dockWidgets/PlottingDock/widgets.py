import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QWidget, QMenu, QAction, \
    QApplication
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pwspy.analysis.analysisResults import AnalysisResultsLoader
from pwspy.apps.PWSAnalysisApp.dockWidgets.PlottingDock.bigPlot import BigPlot
from pwspy.imCube import ImCube
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility import PlotNd


class AspectRatioWidget(QWidget):
    def __init__(self, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self._aspect = aspect

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self._resize(event.size().width())

    def _resize(self, width):
        newHeight = width / self._aspect
        self.setMaximumHeight(newHeight)

    def setAspect(self, aspect: float):
        self._aspect = aspect
        self._resize(self.width())


class AnalysisPlotter:
    def __init__(self, metadata: ICMetaData, analysis: AnalysisResultsLoader = None):
        self.analysis = analysis
        self.metadata = metadata
        self.data = None
        self.analysisField = None

    def changeData(self, field):
        if field != self.analysisField:
            self.analysisField = field
            if field == 'imbd': #Load the imbd from the ICMetadata object
                self.data = self.metadata.getImBd()
            else:
                if self.analysis is None:
                    raise ValueError(f"Analysis Plotter for ImCube {self.metadata.filePath} does not have an analysis file.")
                self.data = getattr(self.analysis, field)
            assert len(self.data.shape) == 2


class LittlePlot(FigureCanvasQTAgg, AnalysisPlotter):
    def __init__(self, metadata: ICMetaData, analysis: AnalysisResultsLoader, title: str, initialField='imbd'):
        AnalysisPlotter.__init__(self, metadata, analysis)
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.im = self.ax.imshow(np.zeros((100, 100)))
        self.title = f"{title} {initialField}"
        self.ax.set_title(self.title, fontsize=8)
        self.ax.yaxis.set_visible(False)
        self.ax.xaxis.set_visible(False)
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.mpl_connect("button_release_event", self.mouseReleaseEvent)
        self.setMinimumWidth(20)
        self.changeData(initialField)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.plotnd = None

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            BigPlot(self.metadata, self.data, self.title, self)

    def changeData(self, field):
        AnalysisPlotter.changeData(self, field)
        t = self.title.split(' ')
        t[-1] = field
        self.title = ' '.join(t)
        self.ax.set_title(self.title, fontsize=8)
        self.im.set_data(self.data)
        self.im.set_clim((np.percentile(self.data, 0.1), np.percentile(self.data, 99.9)))
        self.draw_idle()

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        if self.analysis is not None:
            anPlotAction = QAction("Plot3d Analyzed Reflectance", self)
            anPlotAction.triggered.connect(self.plotAn3d)
            menu.addAction(anPlotAction)
        rawPlotAction = QAction("Plot3d Raw Data", self)
        rawPlotAction.triggered.connect(self.plotRaw3d)
        menu.addAction(rawPlotAction)
        menu.exec(self.mapToGlobal(point))

    def plotAn3d(self):
        self.plotnd = PlotNd(self.analysis.reflectance.data)

    def plotRaw3d(self):
        self.plotnd = PlotNd(ImCube.fromMetadata(self.metadata).data)



if __name__ == '__main__':
    app = QApplication([])
    b = BigPlot(np.random.random((1024, 1024)), 'Title')
    app.exec()