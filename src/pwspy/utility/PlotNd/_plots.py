from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from typing import Tuple, Union
import numpy as np

lw = 0.75

class PlotBase(FigureCanvasQTAgg):
    """An abstract class for the plots in the ND plotter widget. Dimension is the numpy array dimensions associated with this plot. For an image plot it should be a tuple of the two dimensions."""
    def __init__(self, dimensions: Tuple[int, ...]):
        self.figure = Figure()
        self.ax = self.figure.add_subplot(1, 1, 1)
        self.dimensions = dimensions
        self.artists = None  # Derived classes should have a list of all matplotlib artists.
        self.background = None
        super().__init__(self.figure)
        self.mpl_connect('draw_event', self.updateBackground)

    def updateBackground(self, event):
        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.bbox)

    def drawArtists(self):
        for artist in self.artists:
            self.ax.draw_artist(artist)


class ImPlot(PlotBase):
    def __init__(self, shape: Tuple[int, int], dims: Tuple[int ,int]):
        assert len(shape) == 2
        self.shape = shape
        super().__init__(dims)
        self.ax.get_yaxis().set_visible(False)
        self.ax.get_xaxis().set_visible(False)
        self.vLine = self.ax.plot([100, 100], [0, shape[0]], 'r', linewidth=lw, animated=True)[0]
        self.hLine = self.ax.plot([0, shape[1]], [100, 100], 'r', linewidth=lw, animated=True)[0]
        self.im = self.ax.imshow(np.zeros(shape), aspect='auto', animated=True)
        self.ax.set_xlim((0, shape[1]-1))
        self.ax.set_ylim((0, shape[0]-1))
        self.range = (0, 1)
        self.artists = [self.im, self.hLine, self.vLine]
        # self.fig.colorbar(self.im, ax=self.ax)

    def setRange(self, Min, Max):
        self.range = (Min, Max)
        self.im.set_clim(*self.range)

    def setMarker(self, pos: Tuple[float, float]):
        assert len(pos) == 2
        y, x = pos
        self.hLine.set_data([0, self.shape[1]], [y, y])
        self.vLine.set_data([x, x], [0, self.shape[0]])

    def setData(self, data):
        self.im.set_data(data)



class SidePlot(PlotBase):
    def __init__(self, dimLength: int, vertical: bool, dimension: int, invertAxis: bool = False, title: str = None):
        super().__init__((dimension,))
        if title:
            self.ax.set_title(title)
        self.vertical = vertical
        self.dimLength = dimLength
        limFunc = self.ax.set_ylim if vertical else self.ax.set_xlim

        if invertAxis:  # Change the data direction. this can be used to make the image orientation match the orientation of other images.
            limFunc(dimLength-1, 0)
        else:
            limFunc(0, dimLength-1)
        self.range = (0, 1)
        markerData = (self.range, (0, dimLength))
        if self.vertical:
            markerData = markerData[1] + markerData[0]
        self.plot = self.ax.plot([0], [0], animated=True)[0]
        self.markerLine = self.ax.plot(*markerData, color='r', linewidth=lw, animated=True)[0]
        self.artists = [self.plot, self.markerLine]

    def setMarker(self, pos: Tuple[float]):
        assert len(pos) == 1
        data = ((pos, pos), self.range)
        if self.vertical:
            data = (data[1],) + (data[0],)
        self.markerLine.set_data(*data)

    def setRange(self, Min, Max):
        self.range = (Min, Max)
        if self.vertical:
            _ = self.ax.set_xlim
        else:
            _ = self.ax.set_ylim
        _(*self.range)

    def setData(self, data):
        ind = np.arange(self.dimLength)
        if self.vertical:
            data = (data, ind)
        else:
            data = (ind, data)
        self.plot.set_data(*data)

