# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 16:47:22 2019

@author: Nick
"""
from __future__ import annotations
from typing import Tuple, Union, Iterable

import h5py
import numpy as np
import scipy.signal as sps
import matplotlib.pyplot as plt
from matplotlib import widgets
from matplotlib import path
import typing, numbers

from pwspy.imCube.otherClasses import Roi
from matplotlib import patches
import cv2

class ICBase:
    """A class to handle the data operations common to PWS related `image cubes`. Does not contain any file specific
    functionality. uses the generic `index` attribute which can be overridden by derived classes to be wavelength, wavenumber,
    time, etc."""
    _index: tuple
    data: np.ndarray

    def __init__(self, data: np.ndarray, index: tuple, dtype=np.float32):
        assert isinstance(data, np.ndarray)
        self.data = data.astype(dtype)
        self._index = index
        if self.data.shape[2] != len(self.index):
            raise ValueError(f"The length of the index list doesn't match the index axis of the data array. Got {len(self.index)}, expected {self.data.shape[2]}.")

    @property
    def index(self) -> Tuple[float, ...]:
        return self._index

    def plotMean(self) -> Tuple[plt.Figure, plt.Axes]:
        """return a figure and attached axes plotting the mean of the data along the index axis. corresponds to the mean reflectance in most cases."""
        fig, ax = plt.subplots()
        mean = np.mean(self.data, axis=2)
        im = ax.imshow(mean)
        plt.colorbar(im, ax=ax)
        return fig, ax

    def getMeanSpectra(self, mask: Union[Roi, np.ndarray] = None) ->Tuple[np.ndarray, np.ndarray]:
        if isinstance(mask, Roi):
            mask = mask.data
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

    def filterDust(self, kernelRadius: float, pixelSize: float) -> None:
        """Both args are in microns. setting `pixelSize` to one will effectively mean that `kernelRadius` is in
        units of pixels. This is useful if pixel size information is missing."""
        # TODO currently the radius is in units of pixels. change to be in units of microns. Need to make sure this information is saved with each acquisition.
        def _gaussKernel(stdDev: float, radius: int):
            # A gaussian kernel that goes to `stdDev` at a radius of `radius` pixels.
            lenSide = 1 + 2 * radius # The kernel is square. the length of a side will be the center pixel plus the radius twice.
            side = np.linspace(-1, 1, num=lenSide)
            X, Y = np.meshgrid(side, side)
            R = np.sqrt(X ** 2 + Y ** 2)
            k = np.exp(-(R ** 2) / (2 * stdDev**2))
            k = k / k.sum()  # normalize so the total is 1.
            return k

        kernelRadius = kernelRadius / pixelSize #convert from microns to pixels
        cKernelRadius = np.ceil(kernelRadius) # Round up to nearest int. The kernel itself must be sized in units of int pixels
        ratio = kernelRadius / cKernelRadius # The ratio between the desired radius and the rounded radius.
        sigma = ratio # scaling sigma by the ratio ensures that regardless of the pixel dimensions of the kernell, it's sigma parameter will math the kernelRadius. If we wanted the kernel to go out to 2 sigma we would do sigma = 2*ratio
        kernel = _gaussKernel(sigma, cKernelRadius)
        for i in range(self.data.shape[2]):
            m = self.data[:, :, i].mean()  # By subtracting the mean and then adding it after convolution we are effectively padding the convolution with the mean.
            self.data[:, :, i] = sps.convolve(self.data[:, :, i] - m, kernel, mode='same') + m

    def _indicesMatch(self, other: 'ICBase') -> bool:
        return self._index == other._index

    def selIndex(self, start, stop) -> ICBase:
        wv = np.array(self.index)
        iStart = np.argmin(np.abs(wv - start))
        iStop = np.argmin(np.abs(wv - stop))
        iStop += 1  # include the end point
        if iStop >= len(wv):  # Include everything
            iStop = None
        data = self.data[:, :, iStart:iStop]
        index = self.index[iStart:iStop]
        return ICBase(data, index)
        
    def _add(self, other: typing.Union['self.__class__', numbers.Real, np.ndarray]) -> 'self.__class__':
        if isinstance(other, self.__class__):
            if not self._indicesMatch(other):
                raise ValueError(f"{self.__class__} indices are not compatible")
            ret = self.data + other.data
        elif isinstance(other, (numbers.Real, np.ndarray)):
            ret = self.data + other
        else:
            raise NotImplementedError(f"Addition is not supported between {self.__class__} and {type(other)}")
        return ret

    def _sub(self, other: typing.Union['self.__class__', numbers.Real, np.ndarray]) -> 'self.__class__':
        if isinstance(other, self.__class__):
            if not self._indicesMatch(other):
                raise ValueError(f"{self.__class__} indices are not compatible")
            ret = self.data - other.data
        elif isinstance(other, (numbers.Real, np.ndarray)):
            ret = self.data - other
        else:
            raise NotImplementedError(f"Subtraction is not supported between {self.__class__} and {type(other)}")
        return ret

    def _mul(self, other: typing.Union['self.__class__', numbers.Real, np.ndarray]) -> 'self.__class__':
        if isinstance(other, self.__class__):
            if not self._indicesMatch(other):
                raise ValueError(f"{self.__class__} indices are not compatible")
            ret = self.data * other.data
        elif isinstance(other, (numbers.Real, np.ndarray)):
            ret = self.data * other
        else:
            raise NotImplementedError(f"Multiplication is not supported between {self.__class__} and {type(other)}")
        return ret

    __mul__ = None
    __rmul__ = __mul__  # multiplication is commutative. let it work both ways.

    def _truediv(self, other: typing.Union['self.__class__', numbers.Real, np.ndarray]) -> 'self.__class__':
        if isinstance(other, self.__class__):
            if not self._indicesMatch(other):
                raise ValueError(f"{self.__class__} indices are not compatible")
            ret = self.data / other.data
        elif isinstance(other, (numbers.Real, np.ndarray)):
            ret = self.data / other
        else:
            raise NotImplementedError(f"Division is not supported between {self.__class__} and {type(other)}")
        return ret

    def toHdfDataset(self, g: h5py.Group, name: str) -> h5py.Group:
        dset = g.create_dataset(name, data=self.data, compression=3)
        print(f"{self.__class__.__name__} chunking shape: {dset.chunks}")
        dset.attrs['index'] = np.array(self.index)
        dset.attrs['type'] = np.string_(self.__class__.__name__)
        return g

    @classmethod
    def _decodeHdf(cls, d: h5py.Dataset):
        assert 'type' in d.attrs
        assert 'index' in d.attrs
        assert d.attrs['type'].encode() == cls.__name__, f"Got {d.attrs['type']} instead of {cls.__name__}"
        print(f'{cls.__name__} chunks: {d.chunks}')
        return np.array(d), tuple(d.attrs['index'])


    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        return cls(*cls._decodeHdf(d))

    def getTransform(self, other: Iterable['self.__class__'], mask:np.ndarray = None, debugPlots: bool = False) -> Iterable[np.ndarray]:
        """Given an array of other ICBase type objects this function will use OpenCV to calculate the transform from
        each of the other objects to self. The transforms can be inverted using numpy.linalg.inv().
        It will return a list of transforms. Each transform is a 3x3 array in the form returned
        by opencv.findHomography(). a boolean mask can be used to select which areas will be searched for features to be used
        in calculating the transform
        This code is basically a copy of this example, it can probably be improved upon:
        https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_feature2d/py_feature_homography/py_feature_homography.html"""
        #TODO change from homography to affine transform. should be more efficient.
        def to8bit(arr: np.ndarray):
            m = np.percentile(arr, 0.1)
            arr -= m
            M = np.percentile(arr, 99.9)
            arr = arr / M * 255
            arr[arr<0] = 0
            arr[arr>255] = 255
            return arr.astype(np.uint8)
        midIdx = self.index[len(self.index)//2]
        midPlane = to8bit(self.selIndex(midIdx, midIdx).data.squeeze())

        MIN_MATCH_COUNT = 10
        FLANN_INDEX_KDTREE = 0


        # Initiate SIFT detector
        sift = cv2.xfeatures2d.SIFT_create()
        mask = mask.astype(np.uint8)
        kp1, des1 = sift.detectAndCompute(midPlane, mask=mask)

        transforms = []
        for cube in other:
            midPlaneOther = to8bit(cube.selIndex(midIdx, midIdx).data.squeeze())

            # find the keypoints and descriptors with SIFT
            kp2, des2 = sift.detectAndCompute(midPlaneOther, mask=mask)

            index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
            search_params = dict(checks=50)

            flann = cv2.FlannBasedMatcher(index_params, search_params)

            matches = flann.knnMatch(des1, des2, k=2)

            # store all the good matches as per Lowe's ratio test.
            good = []
            for m, n in matches:
                if m.distance < 0.7 * n.distance:
                    good.append(m)

            if len(good) > MIN_MATCH_COUNT:
                src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
                dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)

                M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                transforms.append(M)
                matchesMask = mask.ravel().tolist()

            else:
                print("Not enough matches are found - %d/%d" % (len(good), MIN_MATCH_COUNT))
                matchesMask = None

            if debugPlots:
                h, w = midPlane.shape
                pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
                dst = cv2.perspectiveTransform(pts, M)
                draw_params = dict(matchColor=(0, 255, 0),  # draw matches in green color
                                   singlePointColor=None,
                                   matchesMask=matchesMask,  # draw only inliers
                                   flags=2)
                img2 = cv2.polylines(midPlaneOther, [np.int32(dst)], True, 255, 3, cv2.LINE_AA)
                img3 = cv2.drawMatches(midPlane, kp1, img2, kp2, good, None, **draw_params)
                plt.figure()
                plt.imshow(img3, 'gray')
                plt.show()

        return transforms