# -*- coding: utf-8 -*-
"""
Created on Fri Feb  1 19:37:35 2019

@author: Nick
"""
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation

lw = 0.5

class Base:
    def __init__(self, ax):
        self.ax = ax
        self.artists = None
        self.background = None

    def updateBackground(self):
        self.background = self.ax.figure.canvas.copy_from_bbox(self.ax.bbox)

    def draw(self):
        for artist in self.artists:
            self.ax.draw_artist(artist)

class SidePlot(Base):
    def __init__(self, ax: plt.Axes, dimLength: int, vertical: bool):
        super().__init__(ax)
        self.vertical = vertical
        self.dimLength = dimLength
        self.range = (0, 1)
        markerData = (self.range, (0, dimLength))
        if self.vertical:
            markerData = markerData[1] + markerData[0]
        self.plot = ax.plot([0], [0])[0]
        self.markerLine = ax.plot(*markerData, color='r', linewidth=lw)[0]
        self.artists = [self.plot, self.markerLine]


    def setMarker(self, pos: float):
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

class CenterPlot(Base):
    def __init__(self, ax: plt.Axes, shape):
        super().__init__(ax)
        self.shape = shape
        self.vLine = ax.plot([100, 100], [0, shape[0]], 'r', linewidth=lw)[0]
        self.hLine = ax.plot([0, shape[1]], [100, 100], 'r', linewidth=lw)[0]
        self.im = ax.imshow(np.zeros(shape), aspect='auto')
        ax.set_xlim((0, shape[1]))
        ax.set_ylim((0, shape[0]))
        self.range = (0, 1)
        self.artists = [self.im, self.hLine, self.vLine]

    def setRange(self, Min, Max):
        self.range = (Min, Max)
        self.im.set_clim(*self.range)

    def setMarker(self, x, y):
        self.hLine.set_data([0, self.shape[1]], [y, y])
        self.vLine.set_data([x, x], [0, self.shape[0]])

    def setData(self, data):
        self.im.set_data(data)

class CBar(Base):
    def __init__(self, ax: plt.Axes, im):
        super().__init__(ax)
        self.cbar = plt.colorbar(im, cax=self.ax, orientation='horizontal')
        self.ax.xaxis.set_ticks_position("top")
        self.artists = [None]


#TODO use blitting
class PlotNd(object):
    """A class to conveniently view 3d or greater data."""
    def __init__(self, X: np.ndarray, names=('y', 'x', 'lambda'), initialCoords=None, title=''):
        self.max = self.min = None
        fig = plt.figure(figsize=(6, 6))
        self.fig = fig
        fig.suptitle(title)
        h, w = X.shape[:2]
        self.names = names
        self.extraDims = len(X.shape[2:])
        gs = gridspec.GridSpec(3, 2 + self.extraDims + 1, hspace=0,
                               width_ratios=[w * .2 / (self.extraDims + 1)] * (self.extraDims + 1) + [w, w * .2],
                               height_ratios=[h * .1, h, h * .2], wspace=0)
        ax: plt.Axes = plt.subplot(gs[1, self.extraDims + 1])
        ax.get_xaxis().set_visible(False)
        ax.get_yaxis().set_visible(False)
        self.cp = CenterPlot(ax, X.shape[:2])

        ax: plt.Axes = plt.subplot(gs[1, self.extraDims + 2], sharey=self.cp.ax)
        ax.set_title(names[0])
        ax.yaxis.set_ticks_position('right')
        self.spY = SidePlot(ax, X.shape[0], True)

        ax: plt.Axes = plt.subplot(gs[2, self.extraDims + 1], sharex=self.cp.ax)
        ax.set_xlabel(names[1])
        self.spX = SidePlot(ax, X.shape[1], False)

        ax = plt.subplot(gs[0, self.extraDims + 1])
        self.cbar = CBar(ax, self.cp.im)

        extra = [plt.subplot(gs[1, i]) for i in range(self.extraDims)]
        [extra[i].set_ylim(0, X.shape[2 + i] - 1) for i in range(self.extraDims)]
        [extra[i].set_title(names[2 + i]) for i in range(self.extraDims)]
        self.extra = [SidePlot(ax, X.shape[i+2], True) for i, ax in enumerate(extra)]

        fig.canvas.mpl_connect('key_press_event', self.onpress)
        fig.canvas.mpl_connect('scroll_event', self.onscroll)
        fig.canvas.mpl_connect('button_press_event', self.onclick)
        fig.canvas.mpl_connect('motion_notify_event', self.ondrag)
        fig.canvas.mpl_connect('draw_event', self._update_background)
        self.timer = fig.canvas.new_timer(interval=100)
        self.timer.add_callback(self.increment)
        self.timerRunning = False
        self.fig = fig
        '''Scroll to navigate stacks.\n\nPress "a" to automatically scroll.\n\nLeft click the color bar to set the max color range.\n\nRight click to set the mininum.\n\nPress "r" to reset the color range.\n\nPress 't' to swap the two primary axes.\n\nPress 'y' to rotate the order of the secondary axes.\n\nPress 'u' to rotate the order of all axes, allowing\n\a secondary axis to become a primary axis\n\n\n'''
        self.X = X
        self.resetColor()

        self.coords = tuple(i // 2 for i in X.shape) if initialCoords is None else initialCoords


        self.update(blit=False)
        self.updateLimits()
        plt.pause(0.1)

    def save(self, path, interval=50):
        def f(self, z):
            self.coords = self.coords[:2] + (z,) + self.coords[3:]
            self.update()

        ani = FuncAnimation(self.fig, lambda z: f(self, z), frames=list(range(self.X.shape[2])), blit=False, interval=interval)
        ani.save(path)
        return ani

    def update(self, blit=True):
        self.cp.setData(np.squeeze(self.X[(slice(None), slice(None)) + self.coords[2:]]))
        self.spY.setData(self.X[(slice(None),) + tuple(i for i in self.coords[1:])])
        self.spX.setData(self.X[(self.coords[0], slice(None)) + self.coords[2:]])
        for i, sp in enumerate(self.extra):
            sp.setData(self.X[self.coords[:2 + i] + (slice(None),) + self.coords[3 + i:]])
            sp.setMarker(self.coords[2 + i])
        self.cp.setMarker(self.coords[1], self.coords[0])
        self.spX.setMarker(self.coords[1])
        self.spY.setMarker(self.coords[0])
        if blit:
            self.blit()
        else:
            self.fig.canvas.draw()

    def blit(self):
        """Re-render the axes."""
        for artistManager in [self.spX, self.spY, self.cp] + self.extra:
            if artistManager.background is not None:
                self.fig.canvas.restore_region(artistManager.background)
            artistManager.draw() #Draw the artists
            self.fig.canvas.blit(artistManager.ax.bbox)

    def _update_background(self, event):
        """force an update of the background"""
        for artistManager in [self.spX, self.spY, self.cp] + self.extra:
            artistManager.updateBackground()

    def updateLimits(self):
        self.cp.setRange(self.min, self.max)
        self.spY.setRange(self.min, self.max)
        self.spX.setRange(self.min, self.max)
        for sp in self.extra:
            sp.setRange(self.min, self.max)

    def resetColor(self):
        self.max = np.percentile(self.X[np.logical_not(np.isnan(self.X))], 99.99)
        self.min = np.percentile(self.X[np.logical_not(np.isnan(self.X))], 0.01)
        self.updateLimits()

    def onscroll(self, event):
        if (event.button == 'up') or (event.button == 'down'):
            self.coords = self.coords[:2] + ((self.coords[2] + int(event.step)) % self.X.shape[2],) + (self.coords[3:])
        self.update()

    def onpress(self, event):
        print(event.key)
        if event.key == 'a':
            if self.timerRunning:
                self.timer.stop()
                self.timerRunning = False
            else:
                self.timer.start()
                self.timerRunning = True
        elif event.key == 'r':
            self.resetColor()
            self.update()
        elif event.key == 'u':
            axes = np.roll(np.arange(len(self.X.shape)), 1)
            names = [self.names[i] for i in axes]
            coords = tuple(self.coords[i] for i in axes)
            newX = np.transpose(self.X, axes)
            PlotNd(newX, names, coords)
        elif event.key == 't':
            axes = [1, 0] + list(range(2, len(self.X.shape)))
            names = [self.names[i] for i in axes]
            coords = tuple(self.coords[i] for i in axes)
            newX = np.transpose(self.X, axes)
            PlotNd(newX, names, coords)
        elif event.key == 'y':
            axes = [0, 1] + list(np.roll(np.arange(2, len(self.X.shape)), 1))
            names = [self.names[i] for i in axes]
            coords = tuple(self.coords[i] for i in axes)
            newX = np.transpose(self.X, axes)
            PlotNd(newX, names, coords)

    def onclick(self, event):
        if event.inaxes is None:
            return
        ax = event.inaxes
        x, y = event.xdata, event.ydata
        button = event.button
        self.processMouse(ax, x, y, button, colorbar=True)

    def processMouse(self, ax, x, y, button, colorbar):
        if colorbar:
            if ax == self.cbar.ax:
                if button == 1:
                    self.max = x
                elif button == 3:
                    self.min = x
                self.updateLimits()
                return
        if ax == self.cp.ax:
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

    def increment(self):
        self.coords = (self.coords[0], self.coords[1], (self.coords[2] + 1) % self.X.shape[2]) + self.coords[3:]
        self.update()


if __name__ == '__main__':
    x = np.linspace(-1, 1, num=1000)
    y = np.linspace(-1, 1, num=1000)
    z = np.linspace(-1, 1, num=80)
    t = np.linspace(0, 20, num=1)
    Y, X, Z, T = np.meshgrid(y, x, z, t)
    names = ['y', 'x', 'z', 't']
    R = np.sqrt(X ** 2 + Y ** 2 + Z ** 2)
    A = np.exp(-R) * (.75 + .25 * np.sin(T))
    crop = np.sqrt(X ** 2 + Y ** 2) > .75
    plt.interactive(True)
    '''We can also rotate the array if needed'''
    #    degrees = 35
    #    plane = (0,2) #rotating in the yz plane
    #    A = ndi.rotate(A,degrees, axes=plane)
    #    crop = ndi.rotate(crop,degrees, axes=plane,order = 0,output=np.bool, cval=True)

    A[crop] = np.nan

    p = PlotNd(A, names)  # Input array dimensions should be [y,x,z]
    plt.show(block=True)