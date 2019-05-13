from os import path as osp

import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QWidget, QBoxLayout, QSpacerItem, QGridLayout, QButtonGroup, QPushButton, QMenu, QAction, \
    QSlider, QApplication, QLabel, QDialog, QVBoxLayout, QSpinBox, QDoubleSpinBox, QAbstractSpinBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector

from pwspy.analysis.analysisResults import AnalysisResultsLoader
from pwspy.apps.PWSAnalysisApp.sharedWidgets.rangeSlider import QRangeSlider
from pwspy.imCube import ImCube
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility import PlotNd
from pwspy.utility.matplotlibwidg import MyLasso, AxManager, MyEllipse, mySelectorWidget, AdjustableSelector
import matplotlib.pyplot as plt


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
            BigPlot(self.data, self.title, self)

    def changeData(self, field):
        AnalysisPlotter.changeData(self, field)
        t = self.title.split(' ')
        t[-1] = field
        self.title = t.join(' ')
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


class BigPlot(AnalysisPlotter, QWidget):
    class SaturationDialog(QDialog):
        def __init__(self, parent):
            super().__init__(parent=parent, flags=QtCore.Qt.FramelessWindowHint)
            self.setModal(True)
            l = QVBoxLayout()
            self.numBox = QDoubleSpinBox()
            self.numBox.setValue(0.1)
            self.numBox.setMinimum(0)
            self.numBox.setSingleStep(0.1)
            self.okButton = QPushButton("Ok")
            self.okButton.released.connect(self.accept)
            l.addWidget(QLabel("Saturation %"))
            l.addWidget(self.numBox)
            l.addWidget(self.okButton)
            self.setLayout(l)

        @property
        def value(self):
            return self.numBox.value()

    class RangeDialog(QDialog):
        def __init__(self, parent):
            super().__init__(parent=parent, flags = QtCore.Qt.FramelessWindowHint)
            self.setModal(True)
            l = QGridLayout()
            self.minBox = QDoubleSpinBox()

            self.maxBox = QDoubleSpinBox()
            self.okButton = QPushButton("Ok")
            self.okButton.released.connect(self.accept)
            l.addWidget(QLabel("Min"), 0, 0, 1, 1)
            l.addWidget(QLabel("Max"), 0, 1, 1, 1)
            l.addWidget(self.minBox, 1, 0, 1, 1)
            l.addWidget(self.maxBox, 1, 1, 1, 1)
            l.addWidget(self.okButton, 2, 1, 1, 1)
            self.setLayout(l)

        def show(self):
            for b in [self.minBox, self.maxBox]:
                b.setMaximum(self.parent().slider.max())
                b.setMinimum(self.parent().slider.min())
            self.minBox.setValue(self.parent().slider.start())
            self.maxBox.setValue(self.parent().slider.end())
            super().show()

        @property
        def minimum(self): return self.minBox.value()

        @property
        def maximum(self): return self.maxBox.value()

    def __init__(self,  data: np.ndarray, title: str, parent=None):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        self.setWindowTitle(title)
        layout = QGridLayout()
        self.data = data
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.im = self.ax.imshow(data)
        self.fig.colorbar(self.im, ax=self.ax)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.slider = QRangeSlider(self)
        self.slider.endValueChanged.connect(self.climImage)
        self.slider.startValueChanged.connect(self.climImage)
        self.autoDlg = BigPlot.SaturationDialog(self)
        self.autoDlg.accepted.connect(self.setSaturation)
        self.rangeDlg = BigPlot.RangeDialog(self)
        self.rangeDlg.accepted.connect(self.setRange)
        self.saturationButton = QPushButton("Auto")
        self.saturationButton.released.connect(self.autoDlg.show)
        self.manualRangeButton = QPushButton("Range")
        self.manualRangeButton.released.connect(self.rangeDlg.show)
        layout.addWidget(self.canvas, 0, 0, 8, 8)
        layout.addWidget(QLabel("Color Range"), 9, 0, 1, 1)
        layout.addWidget(self.slider, 9, 1, 1, 6)
        layout.addWidget(self.saturationButton, 9, 7, 1, 1)
        layout.addWidget(self.manualRangeButton, 9, 8, 1, 1)
        layout.addWidget(NavigationToolbar(self.canvas, self), 10, 0, 8, 8)
        layout.setRowStretch(0, 1) #  This causes the plot to take up all the space that isn't needed by the other widgets.
        self.setLayout(layout)

        M = self.data.max()
        self.slider.setMax(M)
        m = self.data.min()
        self.slider.setMin(m)

        self.show()
        self.setSaturation()

    def setSaturation(self):
        percentage = self.autoDlg.value
        m = np.percentile(self.data, percentage)
        M = np.percentile(self.data, 100 - percentage)
        self.slider.setStart(m)
        self.slider.setEnd(M)

    def setRange(self):
        self.slider.setStart(self.rangeDlg.minimum)
        self.slider.setEnd(self.rangeDlg.maximum)

    def climImage(self):
        self.im.set_clim((self.slider.start(), self.slider.end()))
        self.canvas.draw_idle()


class RoiDrawer(AnalysisPlotter, QWidget):
    def __init__(self, metadata: ICMetaData, analysis: AnalysisResultsLoader = None, parent=None, initialField='imbd'):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        AnalysisPlotter.__init__(self, metadata, analysis)
        self.setWindowTitle("What?!")
        layout = QGridLayout()
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.im = self.ax.imshow(np.zeros((100, 100)))
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        # self.axManager = AxManager(self.ax)
        self.buttonGroup = QButtonGroup(self)
        self.lassoButton = QPushButton("L")
        self.ellipseButton = QPushButton("O")
        self.lastButton_ = None
        self.buttonGroup.addButton(self.lassoButton, 1)
        self.buttonGroup.addButton(self.ellipseButton)
        self.buttonGroup.buttonReleased.connect(self.handleButtons)
        [i.setCheckable(True) for i in self.buttonGroup.buttons()]
        self.adjustButton = QPushButton("Adj")
        self.adjustButton.setCheckable(True)
        self.adjustButton.toggled.connect(self.handleAdjustButton)

        layout.addWidget(self.lassoButton, 0, 0, 1, 1)
        layout.addWidget(self.ellipseButton, 0, 1, 1, 1)
        layout.addWidget(self.adjustButton, 0, 2, 1, 1)
        layout.addWidget(self.canvas, 1, 0, 8, 8)
        layout.addWidget(NavigationToolbar(self.canvas, self), 10, 0, 8, 8)
        self.setLayout(layout)
        self.selector: AdjustableSelector = AdjustableSelector(self.ax, MyLasso)

        self.changeData(initialField)

        self.show()

    def handleButtons(self, button):
        if button != self.lastButton_:
            if button is self.lassoButton:
                self.selector.setSelector(MyLasso)
            elif button is self.ellipseButton:
                self.selector.setSelector(MyEllipse)
            self.lastButton_ = button

    def handleAdjustButton(self, checkstate: bool):
        if self.selector is not None:
            self.selector.adjustable = checkstate

    def changeData(self, field):
        AnalysisPlotter.changeData(self, field)
        self.im.set_data(self.data)
        self.im.set_clim((np.percentile(self.data, 0.1), np.percentile(self.data, 99.9)))
        self.canvas.draw_idle()

if __name__ == '__main__':
    app = QApplication([])
    b = BigPlot(np.random.random((1024, 1024)), 'Title')
    app.exec()