from typing import Tuple, List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QPushButton, QDialog, QSpinBox, QLabel
from matplotlib.animation import FuncAnimation
from pwspy.apps.sharedWidgets.rangeSlider import QRangeSlider
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from pwspy.utility.PlotNd._plots import ImPlot, SidePlot
import numpy as np
from pwspy.utility.PlotNd._plots import CBar
from pwspy.utility.PlotNd._canvas import PlotNdCanvas


class PlotNd(QDialog):
    def __init__(self, data: np.ndarray, names: Tuple[str, ...] = ('y', 'x', 'lambda'),
                 initialCoords: Tuple[int, ...] = None, title: str = '', parent: QWidget = None,
                 extraDimIndices: List[np.ndarray] = None):
        super().__init__(parent=parent)
        title = str(title) #Convert to string just in case
        self.setWindowTitle(title)

        self.canvas = PlotNdCanvas(data, names, initialCoords, extraDimIndices)

        self.slider = QRangeSlider(self)
        self.slider.setMaximumHeight(20)
        self.slider.setMax(np.nanmax(data))
        self.slider.setMin(np.nanmin(data))
        self.slider.setEnd(np.nanmax(data))
        self.slider.setStart(np.nanmin(data))
        self.slider.startValueChanged.connect(self._updateLimits)
        self.slider.endValueChanged.connect(self._updateLimits)

        self.resizeButton = QPushButton("Resize")
        self.resizeButton.released.connect(self._resizeDlg)

        layout = QGridLayout()
        layout.addWidget(self.canvas, 0, 0, 8, 8)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self), 10, 0, 1, 8)
        layout.setRowStretch(0, 1)
        layout.addWidget(self.slider, 8, 0, 1, 7)
        layout.addWidget(self.resizeButton, 8, 7, 1, 1)
        self.setLayout(layout)

        self.show()
        self.setFixedSize(self.size())
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

