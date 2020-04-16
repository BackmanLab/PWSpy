import typing
from abc import ABC, abstractmethod

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from typing import Tuple, Union
import numpy as np
import matplotlib.pyplot as plt

lw = 0.75

class PlotBase(ABC):
    """An abstract class for the plots in the ND plotter widget. Dimension is the numpy array dimensions associated with this plot. For an image plot it should be a tuple of the two dimensions."""
    def __init__(self, ax: plt.Axes, dimensions: Tuple[int, ...]):
        self.ax = ax # The axes object that this plot exists on.
        self.dimensions = dimensions # The dimensions of ND-array that this plot visualized. 2d for an image, 1d for a plot
        self.artists = None  # Derived classes should have a list of all matplotlib artists.
        self.background = None

    def updateBackground(self, event):
        """Refresh the background, this is for the purposes of blitting."""
        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.bbox)

    def drawArtists(self):
        """Redraw each matplotlib artist managed by this object."""
        for artist in self.artists:
            self.ax.draw_artist(artist)

    @abstractmethod
    def setRange(self, Min, Max):
        """Set the range of values that can be viewed. this can be a colormap for an image or the yrange for a plot"""
        pass

    @abstractmethod
    def setMarker(self, pos: Tuple):
        """Set the position of marker line. for an image this is 2d. for a plot it is 1d."""
        pass


class ImPlot(PlotBase):
    def __init__(self, ax, verticalIndex, horizontalIndex, dims: Tuple[int, int]):
        super().__init__(ax, dims)
        self.im = None
        self.setIndices(verticalIndex, horizontalIndex)
        self.ax.get_yaxis().set_visible(False)
        self.ax.get_xaxis().set_visible(False)
        self.vLine = self.ax.plot([100, 100], [self._indices[0][0], self._indices[0][-1]], 'r', linewidth=lw, animated=True)[0]
        self.hLine = self.ax.plot([self._indices[1][0], self._indices[1][-1]], [100, 100], 'r', linewidth=lw, animated=True)[0]
        self.im = self.ax.imshow(np.zeros(self.shape), aspect='auto', animated=True, interpolation=None)
        self.range = (0, 1)
        self.artists = [self.im, self.hLine, self.vLine]

    def setRange(self, Min, Max):
        self.range = (Min, Max)
        self.im.set_clim(*self.range)

    def setMarker(self, pos: Tuple[float, float]):
        assert len(pos) == 2
        y, x = pos
        y = self._verticalCoordToValue(y)
        x = self._horizontalCoordToValue(x)
        self.hLine.set_data([self._indices[1][0], self._indices[1][-1]], [y, y])
        self.vLine.set_data([x, x], [self._indices[0][0], self._indices[0][-1]])

    def setData(self, data):
        self.im.set_data(data)

    def setIndices(self, verticalIndex, horizontalIndex):
        self._indices = (tuple(verticalIndex), tuple(horizontalIndex))
        self.shape = (len(verticalIndex), len(horizontalIndex))
        self.ax.set_xlim(self._indices[1][0], self._indices[1][-1])
        self.ax.set_ylim(self._indices[0][0], self._indices[0][-1])
        if self.im:
            self.im.set_extent((horizontalIndex[0], horizontalIndex[-1], verticalIndex[0], verticalIndex[-1]))

    def _horizontalCoordToValue(self, coord):
        """Given a coordinate of the ND-array being visualized ( 0, 1, 2, ...) return the value of this plot's index."""
        return self._indices[1][coord]

    def _verticalCoordToValue(self, coord):
        """Given a coordinate of the ND-array being visualized ( 0, 1, 2, ...) return the value of this plot's index."""
        return self._indices[0][coord]

    def verticalValueToCoord(self, value):
        """Given a value of this plot's index return the nearest corresponding coordinate [0, 1, 2, ...]"""
        coord = np.where(np.abs(self._indices[0] - value) == np.min(np.abs(self._indices[0] - value)))[0]
        return int(coord)

    def horizontalValueToCoord(self, value):
        """Given a value of this plot's index return the nearest corresponding coordinate [0, 1, 2, ...]"""
        coord = np.where(np.abs(self._indices[1] - value) == np.min(np.abs(self._indices[1] - value)))[0]
        return int(coord)

class SidePlot(PlotBase):
    def __init__(self, ax, index: typing.Iterable, vertical: bool, dimension: int, invertAxis: bool = False, title: str = None):
        super().__init__(ax, (dimension,))
        self.vertical = vertical
        self.setIndex(index)
        if title:
            self.ax.set_title(title)
        limFunc = self.ax.set_ylim if vertical else self.ax.set_xlim

        if invertAxis:  # Change the data direction. this can be used to make the image orientation match the orientation of other images.
            limFunc(index[-1], index[0])
        else:
            limFunc(index[0], index[-1])
        self.range = (0, 1)
        markerData = (self.range, (0, self.dimLength))
        if self.vertical:
            markerData = markerData[1] + markerData[0]
        self.plot = self.ax.plot([0], [0], animated=True)[0]
        self.markerLine = self.ax.plot(*markerData, color='r', linewidth=lw, animated=True)[0]
        self.artists = [self.plot, self.markerLine]

    def setMarker(self, pos: Tuple[float]):
        assert len(pos) == 1
        pos = self._coordToValue(pos[0])
        data = ((pos, pos), self.range)
        if self.vertical:
            data = (data[1],) + (data[0],)
        self.markerLine.set_data(*data)

    def _coordToValue(self, coord):
        """Given a coordinate of the ND-array being visualized ( 0, 1, 2, ...) return the value of this plot's index."""
        return self.index[coord]

    def valueToCoord(self, value):
        """Given a value of this plot's index return the nearest corresponding coordinate [0, 1, 2, ...]"""
        coord = np.where(np.abs(self.index - value) == np.min(np.abs(self.index - value)))[0]
        return int(coord)

    def setRange(self, Min, Max):
        self.range = (Min, Max)
        if self.vertical:
            _ = self.ax.set_xlim
        else:
            _ = self.ax.set_ylim
        _(*self.range)

    def setIndex(self, index: typing.Iterable):
        self.index = tuple(index)
        self.dimLength = len(index)
        if self.vertical:
            _ = self.ax.set_ylim
        else:
            _ = self.ax.set_xlim
        _(self.index[0], self.index[-1])

    def setData(self, data):
        self.data = data
        if self.vertical:
            data = (data, self.index)
        else:
            data = (self.index, data)
        self.plot.set_data(*data)

    def getData(self):
        return self.data

    def getIndex(self):
        return self.index

class CBar:
    """The colorbar at the top of the ND plotter."""
    def __init__(self, ax: plt.Axes, im):
        self.ax = ax
        self.cbar = ax.figure.colorbar(im, cax=self.ax, orientation='horizontal')
        self.ax.xaxis.set_ticks_position("top")
        self.artists = [None]

    def draw(self):
        self.ax.xaxis.set_ticks_position("top")