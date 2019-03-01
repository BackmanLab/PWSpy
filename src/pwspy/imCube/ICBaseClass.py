# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 16:47:22 2019

@author: Nick
"""
import numpy as np
import scipy.signal as sps
import matplotlib.pyplot as plt
from matplotlib import widgets
from matplotlib import path


class ICBase:
    def __init__(self, data, index: tuple, dtype=np.float32):
        assert isinstance(data, np.ndarray)
        self.data = data.astype(dtype)
        self._index = index
        if self.data.shape[2] != len(self._index):
            raise ValueError("The length of the index list doesn't match the index axis of the data array")

    @property
    def index(self):
        return self._index

    def plotMean(self):
        fig, ax = plt.subplots()
        mean = np.mean(self.data, axis=2)
        im = ax.imshow(mean)
        plt.colorbar(im, ax=ax)
        return fig, ax

    def getMeanSpectra(self, mask=None):
        if mask is None:
            mask = np.ones(self.data.shape[:-1], dtype=np.bool)
        mean = self.data[mask].mean(axis=0)
        std = self.data[mask].std(axis=0)
        return mean, std

    def selectLassoROI(self, displayIndex=None):
        # display index is used to display a particular z-slice for mask drawing. If None then the mean along Z is displayed.
        mask = np.zeros((self.data.shape[0], self.data.shape[1]), dtype=np.bool)

        if displayIndex is None:
            fig, ax = self.plotMean()
        else:
            fig, ax = plt.subplots()
            ax.imshow(self.data[:, :, displayIndex])
        fig.suptitle("Close to accept ROI")
        x, y = np.meshgrid(np.arange(self.data.shape[0]), np.arange(self.data.shape[1]))
        coords = np.vstack((y.flatten(), x.flatten())).T

        def onSelect(verts):
            p = path.Path(verts)
            ind = p.contains_points(coords, radius=0)
            mask[coords[ind, 1], coords[ind, 0]] = True

        l = widgets.LassoSelector(ax, onSelect, lineprops={'color': 'r'})

        while plt.fignum_exists(fig.number):
            fig.canvas.flush_events()
        return mask

    def selectRectangleROI(self, displayIndex=None, xSlice=None, ySlice=None):
        # display index is used to display a particular z-slice for mask drawing. If None then the mean along Z is displayed.
        # X and Y slice allow manual selection of the range.
        mask = np.zeros((self.data.shape[0], self.data.shape[1]), dtype=np.bool)
        slices = {'y': ySlice, 'x': xSlice}
        if (slices['x'] is not None) and (slices['y'] is not None):
            if not hasattr(slices['x'], '__iter__'):
                slices['x'] = (slices['x'],)
            if not hasattr(slices['y'], '__iter__'):
                slices['y'] = (slices['y'],)
            slices['x'] = slice(*slices['x'])
            slices['y'] = slice(*slices['y'])
            mask[slices['y'], slices['x']] = True
        else:
            if displayIndex is None:
                fig, ax = self.plotMean()
            else:
                fig, ax = plt.subplots()
                ax.imshow(self.data[:, :, displayIndex])
            fig.suptitle("Close to accept ROI")

            def rectSelect(mins, maxes):
                y = [int(mins.ydata), int(maxes.ydata)]
                x = [int(mins.xdata), int(maxes.xdata)]
                slices['y'] = slice(min(y), max(y))
                slices['x'] = slice(min(x), max(x))
                mask[slices['y'], slices['x']] = True

            r = widgets.RectangleSelector(ax, rectSelect)

            while plt.fignum_exists(fig.number):
                fig.canvas.flush_events()
        return mask, (slices['y'], slices['x'])

    def __getitem__(self, slic):
        return self.data[slic]

    def filterDust(self, kernelRadius: int):
        def _gaussKernel(radius: int):
            # A kernel that goes to 1 std. It would be better to go out to 2 or 3 std but then you need a larger kernel which greatly increases convolution time.
            lenSide = 1 + 2 * radius
            side = np.linspace(-1, 1, num=lenSide)
            X, Y = np.meshgrid(side, side)
            R = np.sqrt(X ** 2 + Y ** 2)
            k = np.exp(-(R ** 2) / 2)
            k = k / k.sum()  # normalize so the total is 1.
            return k

        kernel = _gaussKernel(kernelRadius)
        for i in range(self.data.shape[2]):
            m = self.data[:, :,
                i].mean()  # By subtracting the mean and then adding it after convolution we are effectively padding the convolution with the mean.
            self.data[:, :, i] = sps.convolve(self.data[:, :, i] - m, kernel, mode='same') + m

    def _indicesMatch(self, other: 'ICBase') -> bool:
        return self._index == other._index
