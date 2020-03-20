from typing import Tuple, List

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QSizeF, QTimer
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QPushButton, QSpinBox, QLabel, QGraphicsView, \
    QGraphicsScene, QGroupBox, QVBoxLayout, QCheckBox, QButtonGroup
from matplotlib import pyplot
from matplotlib.animation import FuncAnimation

from pwspy.apps.sharedWidgets.rangeSlider import QRangeSlider
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT

import numpy as np
from pwspy.utility.plotting._PlotNd import PlotNdCanvas
from pwspy.utility.matplotlibWidgets import LassoSelector, PointSelector, AdjustableSelector


class MyView(QGraphicsView):
    def __init__(self, plot: PlotNdCanvas):
        super().__init__()
        scene = QGraphicsScene(self)
        scene.addWidget(plot)
        self.plot = plot
        self.setScene(scene)
        # self.resize(1024, 1024)
        # self.resizeEvent(QResizeEvent(self.size(),self.size()))
        self.debounce = QTimer()
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(50)
        self.debounce.timeout.connect(self.resizePlot)

    def resizePlot(self):
        w,h = self.size().width(), self.size().height()
        r = self.scene().sceneRect()
        s = min([w,h])
        r.setSize(QSizeF(s,s))
        self.plot.resize(s,s)
        self.scene().setSceneRect(r)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self.debounce.start()
        super().resizeEvent(event)

        # self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio) $This was orignally all that was needed but the resolution of the plot wasn't right which caused render issues.


    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        #Draw border around the scene for debug purposes
        # painter.save()
        # painter.setPen(QPen(QtCore.Qt.darkGray, 5))
        # painter.drawRect(self.scene().sceneRect())
        # painter.restore()
        super().drawBackground(painter, rect)


class PlotNd(QWidget): #TODO add button to save animation, Docstring
    def __init__(self, data: np.ndarray, names: Tuple[str, ...] = ('y', 'x', 'lambda'),
                 initialCoords: Tuple[int, ...] = None, title: str = '', parent: QWidget = None,
                 extraDimIndices: List[np.ndarray] = None):
        super().__init__(parent=parent)


        self.setWindowTitle(str(title))  # Convert to string just in case

        self.canvas = PlotNdCanvas(data, names, initialCoords, extraDimIndices)
        self.view = MyView(self.canvas)
        self.slider = QRangeSlider(self)
        self.slider.setMaximumHeight(20)
        self.slider.setMax(np.nanmax(data))
        self.slider.setMin(np.nanmin(data))
        self.slider.setEnd(np.nanmax(data))
        self.slider.setStart(np.nanmin(data))
        self.slider.startValueChanged.connect(self._updateLimits)
        self.slider.endValueChanged.connect(self._updateLimits)

        self._lastButton = None
        self.selector = AdjustableSelector(self.canvas.image.ax, self.canvas.image.im, LassoSelector, onfinished=self.selectorFinished)

        self.buttonWidget = QGroupBox("Control", self)
        self.buttonWidget.setLayout(QVBoxLayout())
        check = QCheckBox("Cursor Active")
        self.buttonWidget.layout().addWidget(check)
        check.setChecked(self.canvas.spectraViewActive) #Get the right initial value
        check.stateChanged.connect(lambda state: self.canvas.setSpectraViewActive(state!=0))

        self.buttonGroup = QButtonGroup()
        self.pointButton = QPushButton("Point")
        self.buttonGroup.addButton(self.pointButton)
        self.buttonWidget.layout().addWidget(self.pointButton)

        self.lassoButton = QPushButton("Lasso")
        self.buttonGroup.addButton(self.lassoButton)
        self.buttonWidget.layout().addWidget(self.lassoButton)

        self.noneButton = QPushButton("None")
        self.buttonGroup.addButton(self.noneButton)
        self.buttonWidget.layout().addWidget(self.noneButton)

        for b in self.buttonGroup.buttons():
            b.setCheckable(True)
        self.noneButton.setChecked(True)
        self.buttonGroup.buttonReleased.connect(self.handleButtons)

        self.arWidget = QWidget(self)#AspectRatioWidget(1, self)#AspectRatioWidget(1, self)
        layout = QGridLayout()
        layout.addWidget(self.view, 0, 0, 8, 8)
        layout.addWidget(self.buttonWidget, 0, 8, 8, 1)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self), 10, 0, 1, 8)
        layout.setRowStretch(0, 1)
        layout.addWidget(self.slider, 8, 0, 1, 7)
        self.arWidget.setLayout(layout)
        self.setLayout(QGridLayout())
        self.layout().addWidget(self.arWidget)

        self.show()
        self.ar = self.height() / self.width()

    def _updateLimits(self):
        self.canvas.updateLimits(self.slider.end(), self.slider.start())


    def getAnimation(self, interval: int = 50):
        def f(self: PlotNdCanvas, z: int):
            self.coords = self.coords[:2] + (z,) + self.coords[3:]
            self.updatePlots()

        ani = FuncAnimation(self.canvas.fig, lambda z: f(self.canvas, z), frames=list(range(self.canvas.data.shape[2])), blit=False, interval=interval)
        return ani

    def handleButtons(self, button):

        if button is self.pointButton and button is not self._lastButton:
            self.selector.setSelector(PointSelector)
            self.selector.setActive(True)
        if button is self.lassoButton and button is not self._lastButton:
            self.selector.setSelector(LassoSelector)
            self.selector.setActive(True)
        if button is self.noneButton and button is not self._lastButton:
            self.selector.setActive(False)

        self._lastButton = button

    def selectorFinished(self, verts: np.ndarray):
        from pwspy.dataTypes import Roi

        roi = Roi.fromVerts('nomatter', 0, np.array(verts), self.canvas.data.shape[:2])
        selected = self.canvas.data[roi.mask]
        spec = selected.mean(axis=0)
        fig, ax = pyplot.subplots()
        ax.plot(spec)
        fig.show()
        self.selector.setActive(True)

if __name__ == '__main__':
    import sys
    print("Starting")
    x = np.linspace(0, 1, num=100)
    y = np.linspace(0, 1, num=150)
    z = np.linspace(0, 1, num=101)
    t = np.linspace(0, 1, num=3)
    X, Y, Z, T = np.meshgrid(x, y, z, t)
    arr = np.sin(2 * np.pi * 4 * Z) + .5 * X + np.cos(2*np.pi*4*Y)
    app = QApplication(sys.argv)
    p = PlotNd(arr[:,:,:,0], names=('y', 'x', 'z'), extraDimIndices=[z])
    sys.exit(app.exec_())

