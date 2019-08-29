from typing import Tuple, List
from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication
from apps.sharedWidgets.rangeSlider import QRangeSlider
from apps.sharedWidgets.utilityWidgets import AspectRatioWidget
from matplotlib import gridspec
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from pwspy.utility.PlotNd._plots import ImPlot, SidePlot
import numpy as np
import matplotlib.pyplot as plt
from utility.PlotNd._plots import CBar


class PlotNd(QWidget):
    def __init__(self, data: np.ndarray, names: Tuple[str, ...] = ('y', 'x', 'lambda'),
                 initialCoords: Tuple[int, ...] = None, title: str = '', parent: QWidget = None, extraDimIndices = None):
        assert len(names) == len(data.shape)
        super().__init__(parent=parent)
        self.setWindowTitle(title)

        self.childPlots = []
        self.names = names
        self.max = self.min = None  # The minimum and maximum for the color scaling

        extraDims = len(data.shape[2:])  # the first two axes are the image dimensions. Any axes after that are extra dimensions that can be scanned through


        fig = plt.Figure(figsize=(6, 6))
        self.fig = fig
        h, w = data.shape[:2]
        gs = gridspec.GridSpec(3, 2 + extraDims + 1, hspace=0,
                               width_ratios=[w * .2 / (extraDims + 1)] * (extraDims + 1) + [w, w * .2],
                               height_ratios=[h * .1, h, h * .2], wspace=0)
        ax: plt.Axes = fig.add_subplot(gs[1, extraDims + 1])
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        self.image = ImPlot(ax, data.shape[:2], (0, 1))

        ax: plt.Axes = fig.add_subplot(gs[1, extraDims + 2], sharey=self.image.ax)
        ax.set_title(names[0])
        ax.yaxis.set_ticks_position('right')
        self.spY = SidePlot(ax, data.shape[0], True, 0)

        ax: plt.Axes = fig.add_subplot(gs[2, extraDims + 1], sharex=self.image.ax)
        ax.set_xlabel(names[1])
        self.spX = SidePlot(ax, data.shape[1], False, 1)
        self.spX.ax.set_xlabel(self.names[1])

        ax: plt.Axes = fig.add_subplot(gs[0, extraDims + 1])
        self.cbar = CBar(ax, self.image.im)

        extra = [fig.add_subplot(gs[1, i]) for i in range(extraDims)]
        [extra[i].set_ylim(0, data.shape[2 + i] - 1) for i in range(extraDims)]
        [extra[i].set_title(names[2 + i]) for i in range(extraDims)]
        self.extra = []
        for i, ax in enumerate(extra):
            if extraDimIndices is None:
                self.extra.append(SidePlot(ax, data.shape[i + 2], True, 2 + i))
            else:
                self.extra.append(SidePlot(ax, data.shape[i + 2], True, 2 + i, index=extraDimIndices[i]))

        self.artistManagers = [self.spX, self.spY, self.image] + self.extra

        self.canvas = FigureCanvasQTAgg(fig)


        self.slider = QRangeSlider(self)
        self.slider.setMax(data.max())
        self.slider.setMin(data.min())
        self.slider.setEnd(data.max())
        self.slider.setStart(data.min())
        self.slider.startValueChanged.connect(self.updateLimits)
        self.slider.endValueChanged.connect(self.updateLimits)

        self.arWidget = AspectRatioWidget(1, self)
        layout = QGridLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.slider)
        self.arWidget.setLayout(layout)

        layout = QGridLayout()
        layout.addWidget(self.arWidget)
        self.setLayout(layout)

        self.data = data
        self.resetColor()
        self.coords = tuple(i // 2 for i in data.shape) if initialCoords is None else initialCoords

        self.canvas.mpl_connect('button_press_event', self.onclick)
        self.canvas.mpl_connect('motion_notify_event', self.ondrag)
        self.canvas.mpl_connect('scroll_event', self.onscroll)
        self.canvas.mpl_connect('draw_event', self._updateBackground)


        self.updatePlots(blit=False)
        self.updateLimits()
        self.show()

    def _updateBackground(self, event):
        for artistManager in self.artistManagers:
            artistManager.updateBackground(event)
        self.cbar.draw()

    def updatePlots(self, blit=True):
        for plot in self.artistManagers:
            slic = tuple(c if i not in plot.dimensions else slice(None) for i, c in enumerate(self.coords))
            newData = self.data[slic]
            plot.setData(newData)
            newCoords = tuple(c for i, c in enumerate(self.coords) if i in plot.dimensions)
            plot.setMarker(newCoords)
        if blit:
            self.blit()
        else:
            self.canvas.draw()

    def blit(self):
        """Re-render the axes."""
        for artistManager in self.artistManagers: # The fact that spX is first here makes it not render on click. sometimes not sure why.
            if artistManager.background is not None:
               self.canvas.restore_region(artistManager.background)
            artistManager.drawArtists() #Draw the artists
            self.canvas.blit(artistManager.ax.bbox)

    def updateLimits(self):
        self.min = self.slider.start()
        self.max = self.slider.end()
        self.image.setRange(self.min, self.max)
        self.spY.setRange(self.min, self.max)
        self.spX.setRange(self.min, self.max)
        for sp in self.extra:
            sp.setRange(self.min, self.max)
        self.cbar.draw()
        self.canvas.draw_idle()
        try:
            self.updatePlots()  # This will fail when this is run in the constructor.
        except:
            pass

    def resetColor(self):
        self.max = np.percentile(self.data[np.logical_not(np.isnan(self.data))], 99.99)
        self.min = np.percentile(self.data[np.logical_not(np.isnan(self.data))], 0.01)
        self.updateLimits()

    def onscroll(self, event):
        if (event.button == 'up') or (event.button == 'down'):
            step = int(4 * event.step)
            plot = [plot for plot in self.artistManagers if plot.ax == event.inaxes][0]
            self.coords = tuple((c + step) % self.data.shape[plot.dimensions[0]] if i in plot.dimensions else c for i, c in enumerate(self.coords))
            self.updatePlots()
    #
    # def onpress(self, event):
    #     print(event.key)

    #     elif event.key == 'r':
    #         self.resetColor()
    #         self.update()
    #     elif event.key == 'u':
    #         axes = np.roll(np.arange(len(self.X.shape)), 1)
    #         names = [self.names[i] for i in axes]
    #         coords = tuple(self.coords[i] for i in axes)
    #         newX = np.transpose(self.X, axes)
    #         self.childPlots.append(PlotNd(newX, names, coords))
    #
    #     elif event.key == 't':
    #         axes = [1, 0] + list(range(2, len(self.X.shape)))
    #         names = [self.names[i] for i in axes]
    #         coords = tuple(self.coords[i] for i in axes)
    #         newX = np.transpose(self.X, axes)
    #         self.childPlots.append(PlotNd(newX, names, coords))
    #     elif event.key == 'y':
    #         axes = [0, 1] + list(np.roll(np.arange(2, len(self.X.shape)), 1))
    #         names = [self.names[i] for i in axes]
    #         coords = tuple(self.coords[i] for i in axes)
    #         newX = np.transpose(self.X, axes)
    #         self.childPlots.append(PlotNd(newX, names, coords))
    #
    def onclick(self, event):
        if event.inaxes is None:
            return
        if event.dblclick:
            am = [artistManager for artistManager in self.artistManagers if artistManager.ax == event.inaxes][0]
            if isinstance(am, SidePlot):
                fig, ax = plt.subplots()
                ax.plot(*am.getData())
                self.childPlots.append(fig)
                fig.show()
        ax = event.inaxes
        x, y = event.xdata, event.ydata
        button = event.button
        self.processMouse(ax, x, y, button, colorbar=True)

    def processMouse(self, ax, x, y, button, colorbar):
        if ax == self.image.ax:
            self.coords = (int(y), int(x)) + self.coords[2:]
        elif ax == self.spY.ax:
            self.coords = (int(y),) + self.coords[1:]
        elif ax == self.spX.ax:
            self.coords = (self.coords[0], int(x)) + self.coords[2:]
        elif ax in [sp.ax for sp in self.extra]:
            idx = [sp.ax for sp in self.extra].index(ax)
            sp = [sp for sp in self.extra if sp.ax is ax][0]
            ycoord = sp.valueToCoord(y)
            self.coords = self.coords[:2 + idx] + (int(ycoord),) + self.coords[3 + idx:]
        self.updatePlots()

    def ondrag(self, event):
        if event.inaxes is None:
            return
        if event.button != 1:
            return
        ax = event.inaxes
        x, y = event.xdata, event.ydata
        button = event.button
        self.processMouse(ax, x, y, button, colorbar=False)




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

