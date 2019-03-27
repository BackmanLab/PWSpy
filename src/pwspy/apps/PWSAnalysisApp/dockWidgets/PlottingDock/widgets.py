from os import path as osp

import numpy as np
from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QBoxLayout, QSpacerItem, QGridLayout, QButtonGroup, QPushButton
from matplotlib.backends.backend_qt5 import FigureCanvasQT, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector

from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility.matplotlibwidg import myLasso


class AspectRatioWidget(QWidget):
    def __init__(self, widget: QWidget, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self.aspect = aspect
        self.layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        # add spacer, then your widget, then spacer
        self.layout.addItem(QSpacerItem(0, 0))
        self.layout.addWidget(widget)
        self.layout.addItem(QSpacerItem(0, 0))

    def resizeEvent(self, event: QtGui.QResizeEvent):
        thisAspectRatio = event.size().width() / event.size().height()

        if thisAspectRatio > self.aspect:  # too wide
            self.layout.setDirection(QBoxLayout.LeftToRight)
            widgetStretch = self.height() * self.aspect  # i.e., my width
            outerStretch = (self.width() - widgetStretch) / 2 + 0.5
        else:  # too tall
            self.layout.setDirection(QBoxLayout.TopToBottom)
            widgetStretch = self.width() * (1 / self.aspect)  # i.e., my height
            outerStretch = (self.height() - widgetStretch) / 2 + 0.5

        self.layout.setStretch(0, outerStretch)
        self.layout.setStretch(1, widgetStretch)
        self.layout.setStretch(2, outerStretch)


class LittlePlot(FigureCanvasQT):
    def __init__(self, data: np.ndarray, cell: ICMetaData):
        assert len(data.shape) == 2
        self.fig = Figure()
        self.data = data
        self.cell = cell
        ax = self.fig.add_subplot(1, 1, 1)
        ax.imshow(self.data)
        ax.set_title(osp.split(cell.filePath)[-1])
        ax.yaxis.set_visible(False)
        ax.xaxis.set_visible(False)
        super().__init__(self.fig)
        #        self.layout().addWidget(canvas)
        #        self.setFixedSize(200,200)
        self.mpl_connect("button_release_event", self.mouseReleaseEvent)
        self.setMaximumWidth(200)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            BigPlot(self, self.data)


class BigPlot(QWidget):
    def __init__(self, parent, data):
        super().__init__(parent, QtCore.Qt.Window)
        self.setWindowTitle("What?!")
        layout = QGridLayout()
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.imshow(data)
        self.canvas = FigureCanvasQT(self.fig)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.buttonGroup = QButtonGroup(self)
        self.lassoButton = QPushButton("L")
        self.ellipseButton = QPushButton("O")
        self.lastButton_ = None
        self.buttonGroup.addButton(self.lassoButton, 1)
        self.buttonGroup.addButton(self.ellipseButton)
        self.buttonGroup.buttonReleased.connect(self.handleButtons)
        [i.setCheckable(True) for i in self.buttonGroup.buttons()]

        layout.addWidget(self.lassoButton, 0, 0, 1, 1)
        layout.addWidget(self.ellipseButton, 0, 1, 1, 1)
        layout.addWidget(self.canvas, 1, 0, 8, 8)
        layout.addWidget(NavigationToolbar(self.canvas, self), 10, 0, 8, 8)
        self.setLayout(layout)

        self.selector = None

        self.show()

    def handleButtons(self, button):
        if button != self.lastButton_:
            if button is self.lassoButton:
                self.selector = myLasso(self.ax)
            elif button is self.ellipseButton:
                self.selector = LassoSelector(self.ax)
            self.lastButton_ = button