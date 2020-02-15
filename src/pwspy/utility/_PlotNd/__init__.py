from typing import Tuple, List

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QSize, QSizeF
from PyQt5.QtGui import QResizeEvent, QPen, QBrush
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QPushButton, QDialog, QSpinBox, QLabel, QMainWindow, \
    QSizePolicy, QGraphicsWidget, QGraphicsGridLayout, QGraphicsView, QGraphicsScene, QGroupBox, QVBoxLayout
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from pwspy.apps.sharedWidgets.rangeSlider import QRangeSlider
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT

from pwspy.utility._PlotNd._plots import ImPlot, SidePlot
import numpy as np
from pwspy.utility._PlotNd._plots import CBar
from pwspy.utility._PlotNd._canvas import PlotNdCanvas


class AspectRatioWidget(QWidget):
    def __init__(self, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self._aspect = aspect
        self.enabled = True

    def resizeEvent(self, event: QtGui.QResizeEvent):
        w, h = event.size().width(), event.size().height()
        self._resize(w, h)

    def _resize(self, width, height=None):
        if self.enabled:
            self.enabled=False

            newHeight = width / self._aspect #The ideal height based on the new commanded width
            newWidth = height * self._aspect #the ideal width based on the new commanded height

            #Now determine which of the new dimensions to use.
            if width > newWidth:
                newHeight = newWidth / self._aspect
            else:
                newWidth = newHeight * self._aspect
            super().resize(newWidth, newHeight)
            self.enabled=True

    def setAspect(self, aspect: float):
        self._aspect = aspect
        self._resize(self.width(), self.height())


class MyView(QGraphicsView):
    def __init__(self, plot: PlotNdCanvas):
        super().__init__()
        scene = QGraphicsScene(self)
        scene.addWidget(plot)
        self.plot = plot
        self.plot.resize(1024, 1024) #To avoid pixelation
        self.setScene(scene)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        w,h = event.size().width(), event.size().height()
        r = self.scene().sceneRect()
        s = min([w,h])
        r.setSize(QSizeF(s,s))
        self.plot.resize(s,s)
        self.scene().setSceneRect(r)

        # self.fitInView(self.scene().sceneRect(), QtCore.Qt.KeepAspectRatio) $This was orignally all that was needed but the resolution of the plot wasn't right which caused render issues.


    def drawBackground(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None:
        #Draw border around the scene for debug purposes
        painter.save()
        painter.setPen(QPen(QtCore.Qt.darkGray, 5))
        # painter.setBrush(QBrush())
        painter.drawRect(self.scene().sceneRect())
        painter.restore()
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

        self.buttonWidget = QGroupBox("buttons", self)
        self.buttonWidget.setLayout(QVBoxLayout())
        self.buttonWidget.layout().addWidget(QPushButton("The button"))

        # self.resizeButton = QPushButton("Resize")
        # self.resizeButton.released.connect(self._resizeDlg)

        self.arWidget = QWidget(self)#AspectRatioWidget(1, self)#AspectRatioWidget(1, self)
        layout = QGridLayout()
        layout.addWidget(self.view, 0, 0, 8, 8)
        layout.addWidget(self.buttonWidget, 0, 8, 8, 1)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self), 10, 0, 1, 8)
        layout.setRowStretch(0, 1)
        layout.addWidget(self.slider, 8, 0, 1, 7)
        # layout.addWidget(self.resizeButton, 8, 7, 1, 1)
        self.arWidget.setLayout(layout)
        self.setLayout(QGridLayout())
        self.layout().addWidget(self.arWidget)

        self.show()
        self.ar = self.height() / self.width()

    def _updateLimits(self):
        self.canvas.updateLimits(self.slider.end(), self.slider.start())

    def _resizeDlg(self):
        dlg = ResizeDlg(self, self.height())
        dlg.exec()
        if dlg.result() == QDialog.Accepted:
            size = dlg.sizeValue
            print(size)
            self.setFixedHeight(size)
            self.setFixedWidth(int(size / self.ar))

    def getAnimation(self, interval: int = 50):
        def f(self: PlotNdCanvas, z: int):
            self.coords = self.coords[:2] + (z,) + self.coords[3:]
            self.updatePlots()

        ani = FuncAnimation(self.canvas.fig, lambda z: f(self.canvas, z), frames=list(range(self.canvas.data.shape[2])), blit=False, interval=interval)
        return ani


class ResizeDlg(QDialog):
    def __init__(self, parent: QWidget, initialSize: int):
        super().__init__(parent, flags=QtCore.Qt.FramelessWindowHint)
        self.setWindowTitle("Set Size")
        self.okButton = QPushButton("Ok")
        self.okButton.released.connect(self.accept)
        self.sizeBox = QSpinBox(self)
        self.sizeBox.setMaximum(3000)
        self.sizeBox.setMinimum(200)
        self.sizeBox.setValue(initialSize)

        layout = QGridLayout()
        layout.addWidget(QLabel("Pixels: "), 0, 0, 1, 1)
        layout.addWidget(self.sizeBox, 0, 1, 1, 1)
        layout.addWidget(self.okButton, 1, 0, 1, 2)
        self.setLayout(layout)

        self.sizeValue = initialSize

    def accept(self) -> None:
        self.sizeValue = self.sizeBox.value()
        super().accept()

if __name__ == '__main__':
    import sys
    print("Starting")
    x = np.linspace(0, 1, num=100)
    y = np.linspace(0, 1, num=150)
    z = np.linspace(0, 1, num=101)
    t = np.linspace(0, 1, num=3)
    X, Y, Z, T = np.meshgrid(x, y, z, t)
    arr = np.sin(2 * np.pi * 4 * Z) + .5 * X
    app = QApplication(sys.argv)
    p = PlotNd(arr, names=('y', 'x', 'z', 't'), extraDimIndices=[z,t])
    sys.exit(app.exec_())

