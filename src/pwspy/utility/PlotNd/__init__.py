from typing import Tuple

from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication
# from ._plots import ImPlot, SidePlot
from pwspy.utility.PlotNd._plots import ImPlot, SidePlot
import numpy as np



class PlotNd(QWidget):
    def __init__(self, data: np.ndarray, names: Tuple[str, ...] = ('y', 'x', 'lambda'),
                 initialCoords: Tuple[int, ...] = None, title: str = '',
                 indices: Tuple[np.ndarray] = (None, None, None), parent: QWidget = None):
        assert len(names) == len(data.shape)
        super().__init__(parent=parent)
        self.setWindowTitle(title)

        self.names = names
        self.max = self.min = None  # The minimum and maximum for the color scaling

        self.image = ImPlot(data.shape[:2], (0, 1))
        self.spY = SidePlot(data.shape[0], True, 0, title=self.names[0])
        self.spX = SidePlot(data.shape[1], False, 1, title=self.names[1])

        extraDims = len(data.shape[
                        2:])  # the first two axes are the image dimensions. Any axes after that are extra dimensions that can be scanned through
        self.extra = [SidePlot(data.shape[2 + i], True, 2+i, title=self.names[2 + i]) for i in range(extraDims)]

        self.artistManagers = [self.spX, self.spY, self.image] + self.extra

        layout = QGridLayout()
        layout.addWidget(self.image, 0, extraDims, 1, 1)
        layout.addWidget(self.spY, 0, 1 + extraDims, 1, 1)
        layout.addWidget(self.spX, 1, extraDims, 1, 1)
        for i, plot in enumerate(self.extra):
            layout.addWidget(plot, 0, i, 1, 1)
        self.setLayout(layout)

        self.data = data
        self.resetColor()
        self.coords = tuple(i // 2 for i in X.shape) if initialCoords is None else initialCoords

        for i in self.artistManagers:
            i.mpl_connect('button_press_event', self.onclick)
            i.mpl_connect('motion_notify_event', self.ondrag)
        # fig.canvas.mpl_connect('key_press_event', self.onpress)
            if isinstance(i, SidePlot):
                i.mpl_connect('scroll_event', self.onscroll)


        self.update(blit=False)
        self.updateLimits()
        self.show()

    def update(self, blit=True):
        for plot in self.artistManagers:
            slic = tuple(c if i not in plot.dimensions else slice(None) for i, c in enumerate(self.coords))
            newData = self.data[slic]
            plot.setData(newData)
            newCoords = tuple(c for i, c in enumerate(self.coords) if i in plot.dimensions)
            plot.setMarker(newCoords)
        # for i, sp in enumerate(self.extra):
        #     # sp.setData(self.data[self.coords[:2 + i] + (slice(None),) + self.coords[3 + i:]])
        #     sp.setMarker(self.coords[2 + i])
        # self.image.setMarker(self.coords[1], self.coords[0])
        # self.spX.setMarker(self.coords[1])
        # self.spY.setMarker(self.coords[0])
        if blit:
            self.blit()
        else:
            for i in self.artistManagers:
                i.draw()

    def blit(self):
        """Re-render the axes."""
        for artistManager in self.artistManagers: # The fact that spX is first here makes it not render on click. sometimes not sure why.
            if artistManager.background is not None:
               artistManager.restore_region(artistManager.background)
            artistManager.drawArtists() #Draw the artists
            artistManager.blit(artistManager.ax.bbox)

    # def resize(self, event):
    #     size = min([event.width, event.height])
    #     size = size / self.fig.get_dpi()
    #     self.fig.set_size_inches(size, size)
    #
    def updateLimits(self):
        self.image.setRange(self.min, self.max)
        self.spY.setRange(self.min, self.max)
        self.spX.setRange(self.min, self.max)
        for sp in self.extra:
            sp.setRange(self.min, self.max)
        # self.cbar.draw()
        for artistManager in self.artistManagers:
            artistManager.draw_idle()

    def resetColor(self):
        self.max = np.percentile(self.data[np.logical_not(np.isnan(self.data))], 99.99)
        self.min = np.percentile(self.data[np.logical_not(np.isnan(self.data))], 0.01)
        self.updateLimits()
    #
    def onscroll(self, event): #TODO make so that the correct axis scrolls
        step = int(4 * event.step)
        # plot = [for man in self.artistManagers if man.ax == event.inaxes][0]
        if (event.button == 'up') or (event.button == 'down'):
            self.coords = self.coords[:2] + ((self.coords[2] + int(step)) % self.data.shape[2],) + (self.coords[3:])
        self.update()
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
            print("Double!") #TODO open a better plot of the data.
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
            self.coords = self.coords[:2 + idx] + (int(y),) + self.coords[3 + idx:]
        self.update()

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

    x = np.linspace(0, 1)
    y = np.linspace(0, 1, num=30)
    z = np.linspace(0, 1, num=20)
    t = np.linspace(0, 1, num=10)
    X, Y, Z, T = np.meshgrid(x, y, z, t)
    arr = np.sin(2 * np.pi * 4 * Z) + .5 * X
    app = QApplication(sys.argv)
    p = PlotNd(arr, names=('y', 'x', 'z', 't'))
    sys.exit(app.exec_())

