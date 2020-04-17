from typing import Tuple, List

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QSizeF, QTimer
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication, QPushButton, QSpinBox, QLabel, QGraphicsView, \
    QGraphicsScene, QGroupBox, QVBoxLayout, QCheckBox, QButtonGroup
from matplotlib import pyplot
from matplotlib.animation import FuncAnimation
from qtconsole.inprocess import QtInProcessKernelManager
from qtconsole.jupyter_widget import JupyterWidget

from pwspy.apps.sharedWidgets.rangeSlider import QRangeSlider
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT, FigureCanvasQT
import numpy as np
from pwspy.utility.matplotlibWidgets import LassoSelector, PointSelector, AdjustableSelector
from pwspy.utility.plotting._PlotNd._canvas import PlotNdCanvas
from pwspy.utility.plotting._sharedWidgets import AnimationDlg


class _MyView(QGraphicsView):
    """This is a version of QGraphicsView that takes a Qt FigureCanvas from matplotlib and automatically resized the
    canvas to fill as much of the view as possible. A debounce timer is used to prevent lag due to attempting the resize
    the canvas too quickly. This allows for relatively smooth operation. This is essential for us to include a matplotlib
    plot that can maintain it's aspect ratio within a Qt layout.

    Args:
        plot: A matplotlib FigureCanvas that is compatible with Qt (FigureCanvasQT or FigureCanvasQTAgg)

    """
    def __init__(self, plot: FigureCanvasQT):
        super().__init__()
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        scene = QGraphicsScene(self)
        scene.addWidget(plot)
        self.plot = plot
        self.setScene(scene)
        self._debounce = QTimer()  # If the resizeEvent doesn't reset the timer within the 50ms timeout interval then _resizePlot will be called.
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(50)
        self._debounce.timeout.connect(self._resizePlot)

    def _resizePlot(self):
        """This method is indirectly called by the resizeEvent through the debounce timer and sets the size of the plot
        to maximize its size without changing aspect ratio."""
        w, h = self.size().width(), self.size().height()
        r = self.scene().sceneRect()
        s = min([w, h])  # Get the side length of the biggest square that can fit within the rectangle view area.
        self.plot.resize(s, s)  # Set the plot to the size of the square that fits in view.
        r.setSize(QSizeF(s, s))
        self.scene().setSceneRect(r)  # Set the scene size to the square that fits in view.

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        """Every time that the view is resized this event will fire and start the debounce timer. The timer will only
        actually time out if this event doesn't restart it within the timeout period."""
        self._debounce.start()
        super().resizeEvent(event)


class PlotNd(QWidget): #TODO Docstring
    def __init__(self, data: np.ndarray, names: Tuple[str, ...] = ('y', 'x', 'z'),
                 initialCoords: Tuple[int, ...] = None, title: str = '', parent: QWidget = None,
                 extraDimIndices: List[np.ndarray] = None):
        super().__init__(parent=parent)


        self.setWindowTitle(str(title))  # Convert to string just in case

        if data.dtype == bool:
            data = data.astype(np.uint8)

        self.console = None

        self.canvas = PlotNdCanvas(data, names, initialCoords, extraDimIndices)
        self.view = _MyView(self.canvas)
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

        self.consoleButton = QPushButton("Open Console")
        self.consoleButton.released.connect(self.openConsole)

        self.rotateButton = QPushButton("Rotate Axes")
        self.rotateButton.released.connect(self.canvas.rollAxes)

        self.saveButton = QPushButton("Save Animation")
        self.saveButton.released.connect(lambda: AnimationDlg(self.canvas.fig, (self._animationUpdaterFunc, range(self.canvas._data.shape[2])), self).exec())

        self.arWidget = QWidget(self)#AspectRatioWidget(1, self)#AspectRatioWidget(1, self)
        layout = QGridLayout()
        layout.addWidget(self.view, 0, 0, 8, 8)
        layout.addWidget(self.buttonWidget, 0, 8, 4, 1)
        layout.addWidget(self.consoleButton, 4, 8)
        layout.addWidget(self.rotateButton, 5, 8)
        layout.addWidget(self.saveButton, 6, 8)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self), 10, 0, 1, 8)
        layout.setRowStretch(0, 1)
        layout.addWidget(self.slider, 8, 0, 1, 7)
        self.arWidget.setLayout(layout)
        self.setLayout(QGridLayout())
        self.layout().addWidget(self.arWidget)

        self.show()
        self.ar = self.height() / self.width()

    def openConsole(self):
        if self.console is None:
            kernel_manager = QtInProcessKernelManager()
            kernel_manager.start_kernel()
            kernel = kernel_manager.kernel
            kernel.gui = 'qt'
            kernel.shell.push({'plot': self})

            kernel_client = kernel_manager.client()
            kernel_client.start_channels()

            def stop():
                kernel_client.stop_channels()
                kernel_manager.shutdown_kernel()
                app.exit()

            self.console = JupyterWidget()
            self.console.kernel_manager = kernel_manager
            self.console.kernel_client = kernel_client
        self.console.show()
        msg = "'''plot: A reference to this PlotNd Object\nDocumentation here: https://pwspy.readthedocs.io/en/dev/generated/generated/generated/pwspy.utility.plotting.PlotNd.html#pwspy.utility.plotting.PlotNd'''"
        self.console.do_execute(f"print('');print('');print({msg})", True, 0)
        self.console.activateWindow()  # This should bring the window to the front

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        if self.console is not None:
            self.console.close()
        super().closeEvent(a0)

    def _updateLimits(self):
        self.canvas.updateLimits(self.slider.end(), self.slider.start())

    def _animationUpdaterFunc(self, z: int):
        self.canvas.coords = self.canvas.coords[:2] + (z,) + self.canvas.coords[3:]
        self.canvas.updatePlots()

    def getAnimation(self, interval: int = 50):
        ani = FuncAnimation(self.canvas.fig, self._animationUpdaterFunc, frames=list(range(self.canvas._data.shape[2])), blit=False, interval=interval)
        return ani

    def handleButtons(self, button):
        """Document me"""

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
        """Document me"""
        from pwspy.dataTypes import Roi

        roi = Roi.fromVerts('nomatter', 0, np.array(verts), self.canvas._data.shape[:2])
        selected = self.canvas._data[roi.mask]
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
    z = np.linspace(0, 3, num=101)
    t = np.linspace(0, 1, num=3)
    X, Y, Z, T = np.meshgrid(x, y, z, t)
    arr = np.sin(2 * np.pi * 4 * Z) + .5 * X + np.cos(2*np.pi*4*Y)
    app = QApplication(sys.argv)
    p = PlotNd(arr[:,:,:,0], names=('y', 'x', 'z'), extraDimIndices=[z])
    sys.exit(app.exec_())

