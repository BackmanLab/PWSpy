from os import path as osp

import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QBoxLayout, QSpacerItem, QGridLayout, QButtonGroup, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector

from pwspy.analysis.analysisResults import AnalysisResultsLoader
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility.matplotlibwidg import MyLasso, AxManager, MyEllipse, mySelectorWidget, AdjustableSelector


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
    def __init__(self, analysis: AnalysisResultsLoader):
        self.analysis = analysis
        self.data = None
        self.analysisField = None

    def changeActiveAnalysisField(self, field):
        self.analysisField = field
        self.data = getattr(self.analysis, field)
        assert len(self.data.shape) == 2


class LittlePlot(FigureCanvasQTAgg, AnalysisPlotter):
    def __init__(self, analysis: AnalysisResultsLoader, title: str, initialField='rms'):
        AnalysisPlotter.__init__(self, analysis)
        self.fig = Figure()
        ax = self.fig.add_subplot(1, 1, 1)
        self.im = ax.imshow(np.zeros((100,100)))
        ax.set_title(title, fontsize=8)
        ax.yaxis.set_visible(False)
        ax.xaxis.set_visible(False)
        FigureCanvasQTAgg.__init__(self, self.fig)
        self.mpl_connect("button_release_event", self.mouseReleaseEvent)
        self.setMinimumWidth(20)
        self.changeActiveAnalysisField(initialField)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            BigPlot(self.analysis, self)

    def changeActiveAnalysisField(self, field):
        AnalysisPlotter.changeActiveAnalysisField(self, field)
        self.im.set_data(self.data)
        self.im.set_clim((np.percentile(self.data, 0.1), np.percentile(self.data, 99.9)))
        self.draw_idle()

class BigPlot(AnalysisPlotter, QWidget):
    def __init__(self, analysis: AnalysisResultsLoader, parent=None, initialField='rms'):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        AnalysisPlotter.__init__(self, analysis)
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

        self.changeActiveAnalysisField(initialField)

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

    def changeActiveAnalysisField(self, field):
        AnalysisPlotter.changeActiveAnalysisField(self, field)
        self.im.set_data(self.data)
        self.im.set_clim((np.percentile(self.data, 0.1), np.percentile(self.data, 99.9)))
        self.canvas.draw_idle()