# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations
import copy
import json
import logging
import multiprocessing as mp
import numbers
import os
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional, Union, Type

import h5py
import numpy as np
import pandas as pd
import scipy as sp
import tifffile as tf
from matplotlib import pyplot as plt, widgets
from scipy import interpolate as spi
from scipy.io import savemat
from . import _metadata as pwsdtmd
from . import _other
if typing.TYPE_CHECKING:
    from ..utility.reflection import Material


class ICBase(ABC): #TODO add a `completeNormalization` method
    """A class to handle the data operations common to PWS related `image cubes`. Does not contain any file specific
    functionality. uses the generic `index` attribute which can be overridden by derived classes to be wavelength, wavenumber,
    time, etc.

    Args:
        data (np.ndarray): A 3-dimensional array containing the data the dimensions should be [Y, X, Z] where X and Y are the spatial coordinates of the image
            and Z corresponds to the `index` dimension, e.g. wavelength, wavenumber, time, etc.
        index (tuple(Number)): A tuple containing the values of the index for the data. This could be a tuple of wavelength values, times (in the case of Dyanmics), etc.
        dtype (type): the data type that the data should be stored as. The default is numpy.float32.
    """
    _index: tuple
    data: np.ndarray

    def __init__(self, data: np.ndarray, index: tuple, dtype=np.float32):
        assert isinstance(data, np.ndarray)
        self.data = data.astype(dtype)
        self._index = index
        if self.data.shape[2] != len(self.index):
            raise ValueError(f"The length of the index list doesn't match the index axis of the data array. Got {len(self.index)}, expected {self.data.shape[2]}.")

    @property
    @abstractmethod
    def _hdfTypeName(self) -> str:
        """Each class of this type should have a unique constant name which will be used to identify it when saved as HDF."""
        pass

    @property
    def index(self) -> Tuple[float, ...]:
        """

        Returns:
            The values of the datacube's index
        """
        return self._index

    def plotMean(self) -> Tuple[plt.Figure, plt.Axes]:
        """

        Returns:
            A figure and attached axes plotting the mean of the data along the index axis.
                corresponds to the mean reflectance in most cases.
        """
        fig, ax = plt.subplots()
        mean = np.mean(self.data, axis=2)
        im = ax.imshow(mean)
        plt.colorbar(im, ax=ax)
        return fig, ax

    def getMeanSpectra(self, mask: Optional[Union[_other.Roi, np.ndarray]] = None) ->Tuple[np.ndarray, np.ndarray]:
        """Calculate the average spectra within a region of the data.

        Args:
            mask: An optional other.Roi or boolean numpy array used to select pixels from the X and Y dimensions of the data array.
                If left as None then the full data array will be used as the region.

        Returns:
            The average spectra within the region, the standard deviation of the spectra within the region
        """
        if isinstance(mask, _other.Roi):
            mask = mask.mask
        if mask is None: #Make a mask that includes everything
            mask = np.ones(self.data.shape[:-1], dtype=np.bool)
        mean = self.data[mask].mean(axis=0)
        std = self.data[mask].std(axis=0)
        return mean, std

    def selectLassoROI(self, displayIndex: typing.Optional[int] = None, clim: typing.Sequence = None) -> np.ndarray:
        """
        Allow the user to draw a `freehand` ROI on an image of the acquisition.

        Args:
            displayIndex: Display a particular z-slice of the array for mask drawing. If `None` then the mean along Z is displayed.

        Returns:
            An array of vertices of the polygon drawn.
        """
        Verts = [None]
        if displayIndex is None:
            displayIndex = self.data.shape[2]//2
        fig, ax = plt.subplots()
        data = self.data[:, :, displayIndex]
        ax.imshow(data, clim=[np.percentile(data, 1), np.percentile(data, 99)])
        fig.suptitle("Close to accept ROI")

        def onSelect(verts):
            Verts[0] = verts

        l = widgets.LassoSelector(ax, onSelect, lineprops={'color': 'r'})
        fig.show()
        while plt.fignum_exists(fig.number):
            fig.canvas.flush_events()
        return np.array(Verts[0])

    def selectRectangleROI(self, displayIndex: typing.Optional[int] = None) -> np.ndarray:
        """
        Allow the user to draw a rectangular ROI on an image of the acquisition.

        Args:
            displayIndex (int): is used to display a particular z-slice for mask drawing. If None then the mean along Z is displayed. Returns an array of vertices of the rectangle.

        Returns:
            np.ndarray: An array of the 4 XY vertices of the rectangle.
        """
        verts = [None]

        if displayIndex is None:
           displayIndex = self.data.shape[2]//2
        fig, ax = plt.subplots()
        ax.imshow(self.data[:, :, displayIndex])
        fig.suptitle("Close to accept ROI")

        def rectSelect(mins, maxes):
            verts[0] = ((mins.ydata, mins.xdata), (maxes.ydata, mins.xdata), (maxes.ydata, maxes.xdata), (mins.ydata, maxes.xdata))

        r = widgets.RectangleSelector(ax, rectSelect)
        fig.show()
        while plt.fignum_exists(fig.number):
            fig.canvas.flush_events()
        return np.array(verts[0])

    def selectPointROI(self, side: int = 3, displayIndex: Optional[int] = None):
        """
        Allow the user to select a single point on an image of the acquisition.

        Args:
            side (int): The length (in pixels) of the sides of the square that is used for selection.
            displayIndex (Optional[int]): The z-slice of the 3d array which should be displayed

        Returns:
            np.ndarray: An array of the 4 XY vertices of the square.
        """
        from mpl_qt_viz.roiSelection import PointCreator
        verts = [None]
        if displayIndex is None:
           displayIndex = self.data.shape[2]//2
        fig, ax = plt.subplots()
        ax.imshow(self.data[:, :, displayIndex])
        fig.suptitle("Close to accept ROI")
        def select(Verts, handles):
            verts[0] = Verts
        sel = PointCreator(ax, onselect=select, sideLength=side)
        sel.set_active(True)
        fig.show()
        while plt.fignum_exists(fig.number):
            fig.canvas.flush_events()
        return np.array(verts[0])

    def __getitem__(self, slic):
        return self.data[slic]

    def filterDust(self, sigma: float, pixelSize: float):
        """Blurs the data cube in the X and Y dimensions. Often used to remove the effects of dust on a normalization.

        Args:
            sigma: This specifies the radius of the gaussian filter used for blurring. The units of the value are determined by `pixelSize`
            pixelSize: The pixel size in microns. Settings this to 1 will effectively causes sigma to be in units of pixels rather than microns."""
        from scipy import ndimage
        sigma = sigma / pixelSize  # convert from microns to pixels
        for i in range(self.data.shape[2]):
            self.data[:, :, i] = ndimage.filters.gaussian_filter(self.data[:, :, i], sigma, mode='reflect')

    def _indicesMatch(self, other: 'ICBase') -> bool:
        """This check is performed before allowing many arithmetic operations between two data cubes. Makes sure that the Z-axis of the two cubes match."""
        return self._index == other._index

    def selIndex(self, start: float, stop: float) -> typing.Tuple[np.ndarray, typing.Sequence]:
        """
        Args:
            start: The beginning value of the index in the new object.
            stop: The ending value of the index in the new object.
        Returns:
            A new instance of ICBase with only data from `start` to `stop` in the `index`."""
        wv = np.array(self.index)
        iStart = np.argmin(np.abs(wv - start))
        iStop = np.argmin(np.abs(wv - stop))
        iStop += 1  # include the end point
        if iStop >= len(wv):  # Include everything
            iStop = None
        data = self.data[:, :, iStart:iStop]
        index = self.index[iStart:iStop]
        return data, index

    def _add(self, other: typing.Union['self.__class__', numbers.Real, np.ndarray]) -> 'self.__class__':  #TODO these don't return the right datatype. They should probably just be gotten rid of
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

    def __add__(self, other):
        ret = self._add(other)
        new = copy.deepcopy(self)
        new.data = ret
        return new

    def __sub__(self, other):
        ret = self._sub(other)
        new = copy.deepcopy(self)
        new.data = ret
        return new

    def __mul__(self, other):
        ret = self._mul(other)
        new = copy.deepcopy(self)
        new.data = ret
        return new

    __rmul__ = __mul__  # multiplication is commutative. let it work both ways.

    def __truediv__(self, other):
        ret = self._truediv(other)
        new = copy.deepcopy(self)
        new.data = ret
        return new

    def toHdfDataset(self, g: h5py.Group, name: str, fixedPointCompression: bool = True, compression: str = None) -> h5py.Group:
        """
        Save the data of this class to a new HDF dataset.

        Args:
            g (h5py.Group): the parent HDF Group of the new dataset.
            name (str): the name of the new HDF dataset in group `g`.
            fixedPointCompression (bool): if True then save the data in a special 16bit fixed-point format. Testing has shown that this has a
                maximum conversion error of 1.4e-3 percent. Saving is ~10% faster but requires only 50% the hard drive space.
            compression: The value of this argument will be passed to h5py.create_dataset for numpy arrays. See h5py documentation for available options.

        Returns:
            h5py.Group: This is the the same h5py.Group that was passed in a `g`. It should now have a new dataset by the name of 'name'
        """

        if fixedPointCompression:
            # Scale data to span the full range of an unsigned 16bit integer. save as integer and save the min and max
            # needed to scale back to the original data. Testing has shown that this has a maximum conversion error of 1.4e-3 percent.
            # Saving is ~10% faster but requires only 50% the hard drive space. Time can be traded for space by using compression
            # when creating the dataset
            m = self.data.min()
            M = self.data.max()
            fpData = self.data - m
            fpData = fpData / (M - m)
            fpData *= (2 ** 16 - 1)
            fpData = fpData.astype(np.uint16)
            dset = g.create_dataset(name, data=fpData, compression=compression)  # , chunks=(64,64,self.data.shape[2]), compression=2)
            dset.attrs['index'] = np.array(self.index)
            dset.attrs['type'] = np.string_(f"{self._hdfTypeName}_fp")
            dset.attrs['min'] = m
            dset.attrs['max'] = M
        else:
            dset = g.create_dataset(name, data=self.data, compression=compression)
            dset.attrs['index'] = np.array(self.index)
            dset.attrs['type'] = np.string_(self._hdfTypeName)
        return g

    @classmethod
    def decodeHdf(cls, d: h5py.Dataset) -> Tuple[np.array, Tuple[float, ...]]:
        """
        Load a new instance of ICBase from an `h5py.Dataset`

        Args:
            d: The dataset that the ICBase has been saved to

        Returns:
            A tuple containing: (data: The 3D array of `data`,  index: A tuple containing the `index`)
        """
        assert 'type' in d.attrs
        assert 'index' in d.attrs
        if d.attrs['type'].decode() == cls._hdfTypeName: #standard decoding
            return np.array(d), tuple(d.attrs['index'])
        elif d.attrs['type'].decode() == f"{cls._hdfTypeName}_fp": #Fixed point decoding
            M = d.attrs['max']
            m = d.attrs['min']
            arr = np.array(d)
            arr = arr.astype(np.float32) / (2 ** 16 - 1)
            arr *= (M - m)
            arr += m
            return arr, tuple(d.attrs['index'])
        else:
            raise TypeError(f"Got {d.attrs['type'].decode()} instead of {cls._hdfTypeName}")


class ICRawBase(ICBase, ABC):
    """This class represents data cubes which are not derived from other data cubes. They represent raw acquired data that exists as data files on the computer.
    For this reason they may need to have hardware specific corrections applied to them such as normalizing out exposure time, linearizing camera counts,
    subtracting dark counts, etc. The most important change is the addition of `metadata`.

    Args:
        data: A 3-dimensional array containing the data. The dimensions should be [Y, X, Z] where X and Y are the spatial coordinates of the image
            and Z corresponds to the `index` dimension, e.g. wavelength, wavenumber, time, etc.
        index: A tuple containing the values of the index for the data. This could be a tuple of wavelength values, times (in the case of Dynamics), etc.
        metadata: The metadata object associated with this data object.
        processingStatus: An object that keeps track of which processing steps and corrections have been applied to this object.
        dtype (type): the data type that the data should be stored as. The default is numpy.float32.
    """

    @dataclass
    class ProcessingStatus:
        """Keeps track of which processing steps have been applied to an `ICRawBase` object.
        By default none of these things have been done for raw data"""
        cameraCorrected: bool = False
        normalizedByExposure: bool = False
        extraReflectionSubtracted: bool = False
        normalizedByReference: bool = False

        def toDict(self) -> dict:
            return {'camCorrected': self.cameraCorrected, 'exposureNormed': self.normalizedByExposure, 'erSubtracted': self.extraReflectionSubtracted, 'refNormed': self.normalizedByReference}

        @classmethod
        def fromDict(cls, d: dict) -> ICBase.ProcessingStatus:
            return cls(cameraCorrected=d['camCorrected'], normalizedByExposure=d['exposureNormed'], extraReflectionSubtracted=d['erSubtracted'], normalizedByReference=d['refNormed'])

    def __init__(self, data: np.ndarray, index: tuple, metadata: pwsdtmd.MetaDataBase, processingStatus: ProcessingStatus=None, dtype=np.float32):
        super().__init__(data, index, dtype)
        self.metadata = metadata
        if processingStatus:
            self.processingStatus = processingStatus
        else:
            self.processingStatus = ICRawBase.ProcessingStatus(False, False, False, False)

    def normalizeByExposure(self):
        """This is one of the first steps in most analysis pipelines. Data is divided by the camera exposure.
        This way two ImCube that were acquired at different exposure times will still be on equivalent scales."""
        if not self.processingStatus.cameraCorrected:
            raise Exception(
                "This ImCube has not yet been corrected for camera effects. are you sure you want to normalize by exposure?")
        if not self.processingStatus.normalizedByExposure:
            self.data = self.data / self.metadata.exposure
        else:
            raise Exception("The ImCube has already been normalized by exposure.")
        self.processingStatus.normalizedByExposure = True

    def correctCameraEffects(self, correction: _other.CameraCorrection = None, binning: int = None):
        """Subtracts the darkcounts from the data. count is darkcounts per pixel. binning should be specified if
        it wasn't saved in the micromanager metadata. Both method arguments should be able to be loaded automatically
        from the metadata but for older data files they will need to be supplied manually.

        Args:
            correction: The cameracorrection object providing information on how to correct the data.
            binning: The binning that the raw data was imaged at. 2 = 2x2 binning, 3 = 3x3 binning, etc.
        """
        if self.processingStatus.cameraCorrected:
            raise Exception("This ImCube has already had it's camera correction applied!")
        if binning is None:
            binning = self.metadata.binning
            if binning is None: raise ValueError('Binning metadata not found. Binning must be specified in function argument.')
        if correction is None:
            correction = self.metadata.cameraCorrection
            if correction is None: raise ValueError('other.CameraCorrection metadata not found. Binning must be specified in function argument.')
        count = correction.darkCounts * binning ** 2  # Account for the fact that binning multiplies the darkcount.
        self.data = self.data - count
        if correction.linearityPolynomial is None or correction.linearityPolynomial == (1.0,):
            pass
        else:
            self.data = np.polynomial.polynomial.polyval(self.data, (0.0,) + correction.linearityPolynomial)  # The [0] item is the y-intercept (already handled by the darkcount)
        self.processingStatus.cameraCorrected = True
        return

    @abstractmethod
    def normalizeByReference(self, reference: 'self.__class__'):
        """Normalize the raw data of this data cube by a reference cube to result in data representing
        arbitrarily scaled reflectance.

        Args:
            reference: A reference acquisition. Usually an image taken from a blank piece of glass.
        """
        pass

    @abstractmethod
    def subtractExtraReflection(self, extraReflection: ExtraReflectionCube):
        """
        Subtract the portion of the signal that is due to internal reflections of the optical system from the data.

        Args:
            extraReflection: A calculated data cube indicating in units of camera counts how much of the data is from
                unwanted internal reflections of the system.
        """
        pass

    def performFullPreProcessing(self, reference: 'self.__class__', referenceMaterial: Material, extraReflectance: ExtraReflectanceCube, cameraCorrection: typing.Optional[_other.CameraCorrection] = None):
        """
        Use the `subtractExtraReflection`, `normalizeByReference`, `correctCameraEffects`, and `normalizeByExposure`
        methods to perform the standard pre-processing that is done before analysis.

        Note: This will also end up applying corrections to the reference data. If you want to perform pre-processing on a whole batch
        of data then you should implement your own script based on what is done here.

        Args:
            reference: A data cube to be used as a reference for normalization. Usually an image of a blank dish with cell media or air.
            referenceMaterial: The material that was imaged in the reference dish. The theoretically expected reflectance will be calculated
                assuming a "Glass/{Material}" reflective interface.
            extraReflectance: The data cube containing system internal reflectance calibration information about the specific system
                configuration that the data was taken with.
        """
        from pwspy.utility.reflection.reflectanceHelper import getReflectance

        assert not reference.processingStatus.extraReflectionSubtracted
        assert not reference.processingStatus.cameraCorrected
        assert not reference.processingStatus.normalizedByExposure
        reference.correctCameraEffects(cameraCorrection)
        reference.normalizeByExposure()
        self.correctCameraEffects(cameraCorrection)
        self.normalizeByExposure()

        reflection = ExtraReflectionCube.create(extraReflectance, getReflectance(Material.Glass, referenceMaterial), reference)
        reference.subtractExtraReflection(reflection)
        self.subtractExtraReflection(reflection)

        self.normalizeByReference(reference)

    @staticmethod
    @abstractmethod
    def getMetadataClass() -> typing.Type[pwsdtmd.MetaDataBase]:
        """

        Returns:
            The metadata class associated with this subclass of ICRawBase
        """
        pass

    def toHdfDataset(self, g: h5py.Group, name: str, fixedPointCompression: bool = True) -> h5py.Group:
        """
        Save this object into an HDF dataset.

        Args:
            g: The `h5py.Group` object to create a new dataset in.
            name: The name of the new dataset.
            fixedPointCompression: If True then the data will be converted from floating point to 16-bit fixed point.
                This results in approximately half the storage requirements at a very slight loss in precision.

        Returns:
            A reference to the `h5py.Group` passed in as `g`.

        """
        g = ICBase.toHdfDataset(self, g, name, fixedPointCompression)
        self.metadata.encodeHdfMetadata(g[name])
        g[name].attrs['processingStatus'] = np.string_(json.dumps(self.processingStatus.toDict()))
        return g

    @classmethod
    def decodeHdf(cls, d: h5py.Dataset) -> Tuple[np.array, Tuple[float, ...], dict, ProcessingStatus]:
        """
        Load a new instance of ICRawBase from an `h5py.Dataset`

        Args:
            d: The dataset that the ICBase has been saved to

        Returns:
            A tuple containing:
                data: The 3D array of `data`
                index: A tuple containing the `index`
                metadata: A dictionary containing metadata.
                procStatus: The processing status of the object.
        """
        arr, index = super().decodeHdf(d)
        mdDict = cls.getMetadataClass().decodeHdfMetadata(d)
        if 'processingStatus' in d.attrs:
            processingStatus = cls.ProcessingStatus.fromDict(json.loads(d.attrs['processingStatus']))
        else:  # Some old hdf files won't have this field, that's ok.
            processingStatus = None
        return arr, index, mdDict, processingStatus


class DynCube(ICRawBase):
    """A class representing a single acquisition of PWS Dynamics. In which the wavelength is held constant and the 3rd
    dimension of the data is time rather than wavelength. This can be analyzed to reveal information about diffusion rate.
    Contains methods for loading and saving to multiple formats as well as common operations used in analysis.

    Args:
        data: A 3-dimensional array containing the data. The dimensions should be [Y, X, Z] where X and Y are the spatial coordinates of the image
            and Z corresponds to the `index` dimension, e.g. wavelength, wavenumber, time, etc.
        metadata: The metadata object associated with this data object.
        processingStatus: An object that keeps track of which processing steps and corrections have been applied to this object.
        dtype: the data type that the data should be stored as. The default is numpy.float32.
    """

    _hdfTypeName = "DynCube"  # This is used for saving/loading from HDF. Important not to change it or old files will stop working.

    def __init__(self, data, metadata: pwsdtmd.DynMetaData, processingStatus: ICRawBase.ProcessingStatus=None, dtype=np.float32):
        assert isinstance(metadata, pwsdtmd.DynMetaData)
        super().__init__(data, metadata.times, metadata, processingStatus=processingStatus, dtype=dtype)

    @staticmethod
    def getMetadataClass() -> typing.Type[pwsdtmd.DynMetaData]:
        return pwsdtmd.DynMetaData

    @property
    def times(self) -> typing.Tuple[float, ...]:
        """Unlike PWS where we operate along the dimension of wavelength, in dynamics we operate along the dimension of time.

        Returns:
            A tuple of the time values for each 2d slice along the 3rd axis of the `data` array.
        """
        return self.index

    @classmethod
    def fromMetadata(cls, meta: pwsdtmd.DynMetaData, lock: mp.Lock = None) -> DynCube:
        """
        Load a new instance of `DynCube` based on the information contained in a `DynMetaData` object.

        Args:
            meta: The metadata object to be used for loading.
            lock: An optional `Lock` used to synchronize IO operations in multithreaded and multiprocessing applications.

        Returns:
            A new instance of `DynCube`.
        """
        if meta.fileFormat == pwsdtmd.DynMetaData.FileFormats.Tiff:
            return cls.fromTiff(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == pwsdtmd.DynMetaData.FileFormats.RawBinary:
            return cls.fromOldPWS(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat is None:
            return cls.loadAny(meta.filePath, metadata=meta, lock=lock)
        else:
            raise TypeError("Invalid FileFormat")

    @classmethod
    def loadAny(cls, directory: str, metadata: typing.Optional[pwsdtmd.DynMetaData] = None, lock: typing.Optional[mp.Lock] = None) -> DynCube:
        """
        Attempt to load a `DynCube` for any format of file in `directory`

        Args:
            directory: The directory containing the data files.
            metadata: The metadata object associated with this acquisition
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `DynCube`.
        """
        try:
            return DynCube.fromTiff(directory, metadata=metadata, lock=lock)
        except:
            try:
                return DynCube.fromOldPWS(directory, metadata=metadata, lock=lock)
            except:
                raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory, metadata: pwsdtmd.DynMetaData = None,  lock: mp.Lock = None) -> DynCube:
        """Loads from the file format that was saved by the all-matlab version of the Basis acquisition code.
        Data was saved in raw binary to a file called `image_cube`. Some metadata was saved to .mat files called
        `info2` and `info3`.

        Args:
            directory: The directory containing the data files.
            metadata: The metadata object associated with this acquisition
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `DynCube`.
        """
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = pwsdtmd.DynMetaData.fromOldPWS(directory)
            with open(os.path.join(directory, 'image_cube'), 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint16)
            data = data.reshape((metadata.dict['imgHeight'], metadata.dict['imgWidth'], len(metadata.times)), order='F')
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromTiff(cls, directory, metadata: pwsdtmd.DynMetaData = None, lock: mp.Lock = None) -> DynCube:
        """Load a dyanmics acquisition from a tiff file. if the metadata for the acquisition has already been loaded then you can provide
        is as the `metadata` argument to avoid loading it again. the `lock` argument is an optional place to provide a multiprocessing.Lock
        which can be used when multiple files in parallel to avoid giving the hard drive too many simultaneous requests, this is probably not necessary.

        Args:
            directory: The directory containing the data files.
            metadata: The metadata object associated with this acquisition
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `DynCube`.
        """
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = pwsdtmd.DynMetaData.fromTiff(directory)
            if os.path.exists(os.path.join(directory, 'dyn.tif')):
                path = os.path.join(directory, 'dyn.tif')
            else:
                raise OSError("No Tiff file was found at:", directory)
            with tf.TiffFile(path) as tif:
                data = np.rollaxis(tif.asarray(), 0, 3)  # Swap axes to match y,x,lambda convention.
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    def normalizeByReference(self, reference: Union[DynCube, np.ndarray]):
        """This method can accept either a DynCube (in which case it's average over time will be calculated and used for
        normalization) or a 2d numpy Array which should represent the average over time of a reference DynCube. The array
        should be 2D and its shape should match the first two dimensions of this DynCube.

        Args:
            reference: Reference data for normalization. Usually an image of a blank piece of glass.
        """
        logger = logging.getLogger(__name__)
        if self.processingStatus.normalizedByReference:
            raise Exception("This cube has already been normalized by a reference.")
        if not self.processingStatus.cameraCorrected:
            logger.warning("This cube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not self.processingStatus.normalizedByExposure:
            logger.warning("This cube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        if isinstance(reference, DynCube):
            if not reference.processingStatus.cameraCorrected:
                logger.warning("The reference cube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
            if not reference.processingStatus.normalizedByExposure:
                logger.warning("The reference cube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
            mean = reference.data.mean(axis=2)
        elif isinstance(reference, np.ndarray):
            assert len(reference.shape) == 2
            assert reference.shape[0] == self.data.shape[0]
            assert reference.shape[1] == self.data.shape[1]
            mean = reference
        else:
            raise TypeError(f"`reference` must be either DynCube or numpy.ndarray, not {type(reference)}")
        self.data = self.data / mean[:, :, None]
        self.processingStatus.normalizedByReference = True

    def subtractExtraReflection(self, extraReflection: np.ndarray): # Inherit docstring
        assert self.data.shape[:2] == extraReflection.shape
        if not self.processingStatus.normalizedByExposure:
            raise Exception("This DynCube has not yet been normalized by exposure. are you sure you want to normalize by exposure?")
        if not self.processingStatus.extraReflectionSubtracted:
            self.data = self.data - extraReflection[:, :, None]
            self.processingStatus.extraReflectionSubtracted = True
        else:
            raise Exception("The DynCube has already has extra reflection subtracted.")

    def selIndex(self, start, stop) -> DynCube: # Inherit docstring
        data, index = super().selIndex(start, stop)
        md = self.metadata
        md.dict['times'] = index
        return DynCube(data, md)

    def getAutocorrelation(self) -> np.ndarray:
        """
        Returns the autocorrelation function of dynamics data along the time axis. The ACF is calculated using
        fourier transforms using IFFT(FFT(data)*conj(FFT(data)))/length(data).

        Returns:
            A 3D array of the autocorrelation function of the original data.
        """
        data = self.data - self.data.mean(axis=2)[:, :, None]  # By subtracting the mean we get an ACF where the 0-lag value is the variance of the signal.
        F = np.fft.rfft(data, axis=2)
        ac = np.fft.irfft(F * np.conjugate(F), axis=2) / data.shape[2]
        return ac

    def filterDust(self, kernelRadius: float, pixelSize: float = None):
        """
        This method blurs the data of the cube along the X and Y dimensions. This is useful if the cube is being
        used as a reference to normalize other cube. It helps blur out dust and other unwanted small features.

        Args:
            kernelRadius: The `sigma` of the gaussian kernel used for blurring. A greater value results in greater
                blurring. If `pixelSize` is provided then this is in units of `pixelSize`, otherwise it is in units of
                pixels.
            pixelSize: The size (usualy in units of microns) of each pixel in the datacube. This can generally be loaded
                automatically from the metadata.
        """
        if pixelSize is None:
            pixelSize = self.metadata.pixelSizeUm
            if pixelSize is None:
                raise ValueError("DynCube Metadata does not have a `pixelSizeUm` saved. please manually specify pixel size. use pixelSize=1 to make `kernelRadius in units of pixels.")
        super().filterDust(kernelRadius, pixelSize)

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):  # Inherit docstring
        data, index, mdDict, processingStatus = cls.decodeHdf(d)
        md = pwsdtmd.DynMetaData(mdDict, fileFormat=pwsdtmd.DynMetaData.FileFormats.Hdf)
        return cls(data, md, processingStatus=processingStatus)


class ExtraReflectanceCube(ICBase):
    """This class represents a 3D data cube of the extra reflectance in a PWS system.

    Args:
        data: A 3D array of the extra reflectance in the system. It's values are in units of reflectance (between 0 and 1).
        wavelengths: The wavelengths associated with each 2D slice along the 3rd axis of the data array.
        metadata: Metadata
    Attributes:
        metadata (ERMetaData): metadata
        data (ndarray): data
    """

    _hdfTypeName = "ExtraReflectanceCube"  # This is used for saving/loading from HDF. Important not to change it or old files will stop working.

    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: pwsdtmd.ERMetaData):
        assert isinstance(metadata, pwsdtmd.ERMetaData)
        if data.max() > 1 or data.min() < 0:
            logging.getLogger(__name__).warning("Reflectance values must be between 0 and 1")
        self.metadata = metadata
        ICBase.__init__(self, data, wavelengths)

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        """

        Returns:
            The wavelengths corresponding to each element along the 3rd axis of `self.data`.
        """
        return self.index

    @classmethod
    def fromHdfFile(cls, directory: str, name: str) -> ExtraReflectanceCube:
        """
        Load an ExtraReflectanceCube from an HDF5 file. `name` should be the file name, excluding the '_ExtraReflectance.h5' suffix.

        Args:
            directory: The path to the folder containing the HDF file.
            name: The `name` that the cube was saved as.
        Returns:
            A new instance of `ExtraReflectanceCube` loaded from HDF.
        """
        filePath = pwsdtmd.ERMetaData.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[pwsdtmd.ERMetaData.DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    def toHdfFile(self, directory: str, name: str):
        """
        Save an ExtraReflectanceCube to an HDF5 file. The filename will be `name` with the '_ExtraReflectance.h5' suffix.

        Args:
            directory: The path to the folder to save the HDF file to.
            name: The `name` that the cube should be saved as.
        """
        savePath = pwsdtmd.ERMetaData.dirName2Directory(directory, name)
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            self.toHdfDataset(hf)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        """
        Save the ExtraReflectanceCube to an HDF5 dataset. `g` should be an h5py Group or File.

        Args:
            g: The `h5py.Group` to save to.
        """
        g = super().toHdfDataset(g, pwsdtmd.ERMetaData.DATASETTAG)
        g = self.metadata.toHdfDataset(g)
        return g

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None) -> ExtraReflectanceCube:
        """Load the ExtraReflectanceCube from `d`, an HDF5 dataset.

        Args:
            d: The `h5py.Dataset` to load the cube from.
            filePath: The path to the HDF file that the dataset came from.
        Returns:
            A new instance of `ExtraReflectanceCube` loaded from HDF.
        """
        data, index = cls.decodeHdf(d)
        md = pwsdtmd.ERMetaData.fromHdfDataset(d, filePath=filePath)
        return cls(data, index, md)

    @classmethod
    def fromMetadata(cls, md: pwsdtmd.ERMetaData):
        """Load an ExtraReflectanceCube from an ERMetaData object corresponding to an HDF5 file.

        Args:
            md: The metadata to be used for loading the data file.
        """
        directory, name = pwsdtmd.ERMetaData.directory2dirName(md.filePath)
        return cls.fromHdfFile(directory, name)


class ExtraReflectionCube(ICBase):
    """This class is meant to be constructed from an ExtraReflectanceCube along with additional reference measurement
    information. Rather than being in units of reflectance (between 0 and 1) it is in the same units as the reference measurement
    that is provided with, usually counts/ms or just counts.

    Args:
        data: The 3D array of the extra reflection in the system. In units of counts/ms or just counts
        wavelengths: The wavelengths associated with each 2D slice along the 3rd axis of the data array.
        metadata: Metadata
    """

    _hdfTypeName = "ExtraReflectionCube"  # This is used for saving/loading from HDF. Important not to change it or old files will stop working.

    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: pwsdtmd.ERMetaData):
        super().__init__(data, wavelengths)
        self.metadata = metadata

    @classmethod
    def create(cls, reflectance: ExtraReflectanceCube, theoryR: pd.Series, reference: ImCube) -> ExtraReflectionCube:
        """
        Construct and ExtraReflectionCube from an ExtraReflectanceCube and a reference measurement. The resulting
        ExtraReflectionCube will be in the same units as `reference`. `theoryR` should be a spectrum describing the theoretically
        expected reflectance of the reference data cube. Both `theoryR` and `reflectance` should be in units of reflectance
        (between 0 and 1).

        Args:
            reflectance: The `ExtraReflectanceCube` to construct an `ExtraReflectionCube` from.
            theoryR: The theoretically predicted reflectance of material imaged in `reference`.
            reference: A PWS image of a blank glass-{material} interface, usually water.
        Returns:
            A new instance of `ExtraReflectionCube`.
        """
        I0 = reference.data / (np.array(theoryR)[None, None, :] + reflectance.data)  # I0 is the intensity of the illumination source, reconstructed in units of `counts`. this is an inversion of our assumption that reference = I0*(referenceReflectance + extraReflectance)
        data = reflectance.data * I0  # converting extraReflectance to the extra reflection in units of counts
        return cls(data, reflectance.wavelengths, reflectance.metadata)


class ImCube(ICRawBase):
    """
    A class representing a single PWS acquisition. Contains methods for loading and saving to multiple formats as
    well as common operations used in analysis.

    Args:
        data: A 3-dimensional array containing the data. The dimensions should be [Y, X, Z] where X and Y are the spatial coordinates of the image
            and Z corresponds to the `index` dimension, e.g. wavelength, wavenumber, time, etc.
        metadata: The metadata object associated with this data object.
        processingStatus: An object that keeps track of which processing steps and corrections have been applied to this object.
        dtype (type): the data type that the data should be stored as. The default is numpy.float32.
    """

    _hdfTypeName = "ImCube"  # This is used for saving/loading from HDF. Important not to change it or old files will stop working.

    def __init__(self, data, metadata: pwsdtmd.ICMetaData, processingStatus: ICRawBase.ProcessingStatus=None, dtype=np.float32):
        assert isinstance(metadata, pwsdtmd.ICMetaData)
        super().__init__(data, metadata.wavelengths, metadata, processingStatus=processingStatus, dtype=dtype)

    @property
    def wavelengths(self):
        """
        A tuple containing the values of the wavelengths for the data.
        """
        return self.index

    @classmethod
    def loadAny(cls, directory: str, metadata: pwsdtmd.ICMetaData = None,  lock: mp.Lock = None):
        """
        Attempt to load a `ImCube` for any format of file in `directory`

        Args:
            directory: The directory containing the data files.
            metadata: The metadata object associated with this acquisition
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `ImCube`.
        """
        try:
            return ImCube.fromTiff(directory, metadata=metadata, lock=lock)
        except:
            try:
                return ImCube.fromOldPWS(directory, metadata=metadata, lock=lock)
            except:
                try:
                    return ImCube.fromNano(directory, metadata=metadata, lock=lock)
                except:
                    raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory: str, metadata: pwsdtmd.ICMetaData = None,  lock: mp.Lock = None):
        """
        Loads from the file format that was saved by the all-matlab version of the Basis acquisition code.
        Data was saved in raw binary to a file called `image_cube`. Some metadata was saved to .mat files called
        `info2` and `info3`.

        Args:
            directory: The directory containing the data files.
            metadata: The metadata object associated with this acquisition
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `ImCube`.
        """
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = pwsdtmd.ICMetaData.fromOldPWS(directory)
            with open(os.path.join(directory, 'image_cube'), 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint16)
            data = data.reshape((metadata.dict['imgHeight'], metadata.dict['imgWidth'], len(metadata.wavelengths)), order='F')
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromTiff(cls, directory, metadata: pwsdtmd.ICMetaData = None,  lock: mp.Lock = None):
        """
        Loads from a 3D tiff file named `pws.tif`, or in some older data `MMStack.ome.tif`. Metadata can be stored in
        the tags of the tiff file but if there is a pwsmetadata.json file found then this is preferred.
        A multiprocessing.Lock object can be passed to this function so that it will acquire a lock during the
        hard-drive intensive parts of the function. this is useful in multi-core contexts.

        Args:
            directory: The directory containing the data files.
            metadata: The metadata object associated with this acquisition
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `ImCube`.
        """
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = pwsdtmd.ICMetaData.fromTiff(directory)
            if os.path.exists(os.path.join(directory, 'MMStack.ome.tif')):
                path = os.path.join(directory, 'MMStack.ome.tif')
            elif os.path.exists(os.path.join(directory, 'pws.tif')):
                path = os.path.join(directory, 'pws.tif')
            else:
                raise OSError("No Tiff file was found at:", directory)
            with tf.TiffFile(path) as tif:
                data = np.rollaxis(tif.asarray(), 0, 3)  # Swap axes to match y,x,lambda convention.
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromNano(cls, directory: str, metadata: pwsdtmd.ICMetaData = None, lock: mp.Lock = None) -> ImCube:
        """
        Loads from the file format used at NanoCytomics. all data and metadata is contained in a .mat file.

        Args:
            directory: The directory containing the data files.
            metadata: The metadata object associated with this acquisition
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `ImCube`.
        """
        path = os.path.join(directory, 'imageCube.mat')
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = pwsdtmd.ICMetaData.fromNano(directory)
            with h5py.File(path, 'r') as hf:
                data = np.array(hf['imageCube'])
                data = data.transpose((2, 1, 0))  # Re-order axes to match the shape of ROIs and thumbnails.
                data = data.copy(order='C')  # Copying the data to 'C' order has shows to provide some benefit for performance in selecting out spectra.
        finally:
            if lock is not None:
                lock.release()
        return cls(data, metadata)

    @classmethod
    def fromMetadata(cls, meta: pwsdtmd.ICMetaData,  lock: mp.Lock = None) -> ImCube:
        """
        If provided with an ICMetadata object this function will automatically select the correct file loading method
        and will return the associated ImCube.

        Args:
            meta: The metadata to use to load the object from.
            lock: A `Lock` object used to synchronized IO in multithreading and multiprocessing applications.

        Returns:
            A new instance of `ImCube`.
        """
        assert isinstance(meta, pwsdtmd.ICMetaData)
        if meta.fileFormat == pwsdtmd.ICMetaData.FileFormats.Tiff:
            return cls.fromTiff(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == pwsdtmd.ICMetaData.FileFormats.RawBinary:
            return cls.fromOldPWS(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == pwsdtmd.ICMetaData.FileFormats.NanoMat:
            return cls.fromNano(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat is None:
            return cls.loadAny(meta.filePath, metadata=meta, lock=lock)
        else:
            raise TypeError("Invalid FileFormat")

    def toOldPWS(self, directory):
        """
        Save this object to the old .mat based storage format.

        Args:
            directory: The path to the folder to save the data files to.
        """
        if os.path.exists(directory):
            raise OSError("The specified directory already exists.")
        os.mkdir(directory)
        m = self.metadata
        try:
            systemId = m.dict['systemId']
        except KeyError:
            systemId = 0
        info2 = {'info2': np.array([m.wavelengths[0], m.wavelengths[1]-m.wavelengths[0], m.wavelengths[-1], m.exposure, 0, 0, 0, 0, 0, 0],
                                   dtype=np.float64)}
        info3 = {'info3': np.array(
            [systemId, m.exposure, self.data.shape[0], self.data.shape[1], 1970, 1, 1, 0, 0, 0, 0, 0], #Use data 1/1/1970 since we don't have a real acquisition date.
            dtype=np.float64)}  # The new way
        wv = {"WV": m.wavelengths}
        savemat(os.path.join(directory, 'info2'), info2)
        savemat(os.path.join(directory, 'info3'), info3)
        savemat(os.path.join(directory, 'WV'), wv)
        self._saveThumbnail(directory)
        with open(os.path.join(directory, 'image_cube'), 'wb') as f:
            f.write(self.data.astype(np.uint16).tobytes(order='F'))

    def _saveThumbnail(self, directory):
        """Used to save a thumbnail image called `image_bd.tif` this is useful for quickly viewing the cells without
        having to load and process all the data."""
        im = self.data[:, :, self.data.shape[-1] // 2]
        normedIm = im - np.percentile(im, 0.01)  # .01 percent saturation
        normedIm[normedIm<0] = 0 #Don't allow negative values.
        normedIm = normedIm / np.percentile(normedIm, 99.99)
        normedIm[normedIm>1] = 1 #Keep eveything below 1
        normedIm = (normedIm * 255).astype(np.uint8)
        im = tf.TiffWriter(os.path.join(directory, 'image_bd.tif'))
        im.save(normedIm)
        im.close()

    def toTiff(self, outpath: str, dtype=np.uint16):
        """Save the ImCube to the standard TIFF file format.

        Args:
            outpath: The path to save the new TIFF file to.
        """
        im = self.data
        im = im.astype(dtype)
        os.mkdir(outpath)
        self._saveThumbnail(outpath)
        with tf.TiffWriter(open(os.path.join(outpath, 'pws.tif'), 'wb')) as w:
            w.save(np.rollaxis(im, -1, 0), metadata=self.metadata.dict)
        self.metadata.metadataToJson(outpath)

    def selIndex(self, start: float, stop: float) -> ImCube:  # Inherit docstring
        data, index = super().selIndex(start, stop)
        md = copy.deepcopy(self.metadata)  # We are creating a copy of the metadata object because modifying the original metadata object can cause weird issues.
        assert md.dict is not self.metadata.dict
        md.dict['wavelengths'] = index
        return ImCube(data, md)

    @staticmethod
    def getMetadataClass() -> Type[pwsdtmd.ICMetaData]:  # Inherit docstring
        return pwsdtmd.ICMetaData

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        """Load an Imcube from an HDF5 dataset."""
        data, index, mdDict, processingStatus = cls.decodeHdf(d)
        md = pwsdtmd.ICMetaData(mdDict, fileFormat=pwsdtmd.ICMetaData.FileFormats.Hdf)
        return cls(data, md, processingStatus=processingStatus)

    def filterDust(self, kernelRadius: float, pixelSize: float = None) -> None:
        """This method blurs the data of the ImCube along the X and Y dimensions. This is useful if the ImCube is being
        used as a reference to normalize other ImCube. It helps blur out dust adn other unwanted small features.

        Args:
            kernelRadius: The `sigma` of the gaussian kernel used for blurring. A greater value results in greater
                blurring. If `pixelSize` is provided then this is in units of `pixelSize`, otherwise it is in units of
                pixels.
            pixelSize: The size (usualy in units of microns) of each pixel in the datacube. This can generally be loaded
                automatically from the metadata.
        """
        if pixelSize is None:
            pixelSize = self.metadata.pixelSizeUm
            if pixelSize is None:
                raise ValueError("ImCube Metadata does not have a `pixelSizeUm` saved. please manually specify pixel size. use pixelSize=1 to make `kernelRadius in units of pixels.")
        super().filterDust(kernelRadius, pixelSize)

    def normalizeByReference(self, reference: ImCube):
        """Normalize the raw data of this data cube by a reference cube to result in data representing
        arbitrarily scaled reflectance.

        Args:
            reference (ImCube): A reference acquisition (Usually a blank spot on a dish). The data of this acquisition will be divided by the data of the reference
        """
        logger = logging.getLogger(__name__)
        if self.processingStatus.normalizedByReference:
            raise Exception("This ImCube has already been normalized by a reference.")
        if not self.processingStatus.cameraCorrected:
            logger.warning("This ImCube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not self.processingStatus.normalizedByExposure:
            logger.warning("This ImCube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        if not reference.processingStatus.cameraCorrected:
            logger.warning("The reference ImCube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not reference.processingStatus.normalizedByExposure:
            logger.warning("The reference ImCube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        self.data = self.data / reference.data
        self.processingStatus.normalizedByReference = True

    def subtractExtraReflection(self, extraReflection: ExtraReflectionCube):  # Inherit docstring
        assert self.data.shape == extraReflection.data.shape
        if not self.processingStatus.normalizedByExposure:
            raise Exception("This ImCube has not yet been normalized by exposure. Are you sure you want to subtract system reflectance before doing this?")
        if not self.processingStatus.extraReflectionSubtracted:
            self.data = self.data - extraReflection.data
            self.processingStatus.extraReflectionSubtracted = True
        else:
            raise Exception("The ImCube has already has extra reflection subtracted.")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.metadata.idTag})"


class KCube(ICBase):
    """A class representing an ImCube after being transformed from being described in terms of wavelength to
    wavenumber (k-space). Much of the analysis operated in terms of k-space.

    Args:
        data: A 3-dimensional array containing the data. The dimensions should be [Y, X, Z] where X and Y are the spatial coordinates of the image
            and Z corresponds to the `index` dimension, e.g. wavelength, wavenumber, time, etc.
        wavenumbers: A sequence indicating the wavenumber associated with each 2D slice along the 3rd axis of the `data` array.
        metadata: The metadata object associated with this data object.
    """

    _hdfTypeName = "KCube"  # This is used for saving/loading from HDF. Important not to change it or old files will stop working.

    def __init__(self, data: np.ndarray, wavenumbers: Tuple[float], metadata: pwsdtmd.ICMetaData = None):
        self.metadata = metadata #Just saving a reference to the original imcube in case we want to reference it.
        ICBase.__init__(self, data, wavenumbers, dtype=np.float32)

    @classmethod
    def fromImCube(cls, cube: ImCube) -> KCube:
        """
        Convert an ImCube into a KCube. Data is converted from wavelength to wavenumber (1/lambda), interpolation is
        then used to linearize the data in terms of wavenumber.

        Args:
            cube: The `ImCube` object to generate a `KCube` object from.

        Returns:
            A new instance of `KCube`
        """
        # Convert to wavenumber and reverse the order so we are ascending in order. Units of radian/micron
        wavenumbers = (2 * np.pi) / (np.array(cube.wavelengths, dtype=np.float64) * 1e-3)[::-1]
        data = cube.data[:, :, ::-1]
        # Generate evenly spaced wavenumbers
        #        dk = (self.wavenumbers[-1] - self.wavenumbers[0])/(len(self.wavenumbers)-1);
        evenWavenumbers = np.linspace(wavenumbers[0], wavenumbers[-1], num=len(wavenumbers), dtype=np.float64)
        # Interpolate to the evenly spaced wavenumbers
        interpFunc = spi.interp1d(wavenumbers, data, kind='linear', axis=2)
        data = interpFunc(evenWavenumbers)
        return cls(data, tuple(evenWavenumbers.astype(np.float32)), metadata=cube.metadata)

    @property
    def wavenumbers(self) -> Tuple[float, ...]:
        return self.index

    def getOpd(self, isHannWindow: bool, indexOpdStop: int = None, mask: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Calculate the Fourier transform of each spectra. This can be used to get the distance (in terms of OPD) to
        objects that are reflecting light.

        Args:
            isHannWindow: If True, apply a Hann window to the data before the FFT. This reduces spectral resolution but
                improves dynamic range and reduces "frequency leakage".
            indexOpdStop: This parameter is a holdover from the original MATLAB implementation. Truncates the 3rd axis
                of the OPD array.
            mask: A 2D boolean numpy array indicating which pixels should be processed.

        Returns:
            A tuple containing: `opd`: The 3D array of values, `opdIndex`: The sequence of OPD values associated with each
                2D slice along the 3rd axis of the `opd` data.

        """
        dataLength = self.data.shape[2]
        opd = _FFTHelper.getFFTMagnitude(self.data, isHannWindow, normalization=_FFTHelper.Normalization.POWER)
        fftSize = opd.shape[-1]  # Due to FFT interpolation the FFT will be longer than the original data.

        # Isolate the desired values in the OPD.
        opd = opd[:, :, :indexOpdStop]

        if not mask is None:
            opd = opd[mask].mean(axis=0)

        dk = self.wavenumbers[1] - self.wavenumbers[0]  # The interval that our linear array of wavenumbers is spaced by. Units: radians / micron

        # Generate the xval for the current OPD.
        maxOpd = 2 * np.pi / dk  # This is the maximum OPD value we can get with. tighter wavenumber spacing increases OPD range. units of microns
        dOpd = maxOpd / dataLength  # The interval we want between values in our opd vector.
        opdVals = dataLength / 2 * np.array(range(fftSize)) * dOpd / fftSize
        # The above line is how it was written in the matlab code. Couldn't it be simplified down to maxOpd * np.linspace(0, 1, num = fftSize // 2 + 1) / 2 ? I'm not sure what the 2 means though.

        # Above is how the old MATLAB code calculated the frequencies. IMO the code below is simpler and more understandable but we'll stick with the old code.
        # opdVals = np.fft.rfftfreq(fftSize, dk)  # Units: cycles / (radians/microns), equivalent to microns / (radians/cycles)
        # opdVals *= 2 * np.pi  # Units: microns

        opdVals = opdVals[:indexOpdStop]

        opd = opd.astype(self.data.dtype) #Make sure to upscale precision
        opdVals = opdVals.astype(self.data.dtype)
        return opd, opdVals

    def getRMSFromOPD(self, lowerOPD: float, upperOPD: float, useHannWindow: bool = False) -> np.ndarray:
        """
        Use Parseval's Theorem to calculate our signal RMS from the OPD (magnitude of fourier transform). This allows us to calculate RMS using only contributions
        from certain OPD ranges which ideally are correlated with a specific depth into the sample. In practice the large frequency leakage due to our limited
        bandwidth of measurement causes this assumption to break down, but it can still be useful if taken with a grain of salt.

        Args:
            lowerOPD: RMS will be integrated starting at this lower limit of OPD. Note for a reflectance setup like PWS `sampleDepth = OPD / (2 * meanSampleRI)`
            upperOPD: RMS will be integrated up to this upper OPD limit.
            useHannWindow: If False then use no windowing on the FFT to calculate OPD. If True then use and Hann window.

        Returns:
            A 2d numpy array of the signal RMS at each XY location in the image.
        """
        data = self.data - self.data.mean(axis=2)[:, :, None]  # Subtract the mean from every pixel so we are only measuring variance.
        opd = _FFTHelper.getFFTMagnitude(data, useHannWindow, normalization=_FFTHelper.Normalization.POWER)
        dk = self.wavenumbers[1] - self.wavenumbers[0]  # Units of radians / microns
        opdIndex = np.fft.rfftfreq(opd.shape[2], dk)  # Units of microns / (radians / cycles)
        opdIndex *= 2 * np.pi  # Units of microns
        startOpdIdx = np.argmin(np.abs(opdIndex - lowerOPD))  # The index associated with lowerOPD
        stopOpdIdx = np.argmin(np.abs(opdIndex - upperOPD))  # The index associated with upperOPD
        print(stopOpdIdx, startOpdIdx)
        opdSquaredSum = np.sum(opd[:, :, startOpdIdx:stopOpdIdx+1] ** 2, axis=2)  # Parseval's theorem tells us that this is equivalent to the sum of the squares of our original signal
        opdSquaredSum *= len(self.wavenumbers) / opd.shape[2]  # If the original data and opd were of the same length then the above line would be correct. Since the fft may have been upsampled. we need to normalize.
        return np.sqrt(opdSquaredSum)

    @staticmethod
    def fromOpd(opd: np.ndarray, xVals: np.ndarray, useHannWindow: bool):
        """WARNING: This function is untested. it almost certainly doesn't work. Create a KCube from and opd in the form returned by KCube.getOpd. This is useful if you want to do spectral manipulation and then transform back."""
        assert len(xVals.shape) == 1
        fftSize = int(2 ** (np.ceil(np.log2((2 * len(xVals)) - 1))))  # %This is the next size of fft that is  at least 2x greater than is needed but is a power of two. Results in interpolation, helps amplitude accuracy and fft efficiency.
        if useHannWindow: w = np.hanning(len(xVals))
        else: w = np.ones((len(xVals)))
        sig = np.fft.irfft(opd * w[None, None, :], n=fftSize, axis=2)
        #I don't think we need to normalize by the number of elements like we do in getOpd

        # by multiplying by Hann window we reduce the total power of signal. To account for that,
        sig = np.abs(sig / np.sqrt(np.mean(w ** 2)))

        maxWavenumberInterval = 2*np.pi / (xVals[1] - xVals[0])
        dWavenumber = maxWavenumberInterval / len(xVals)
        waveNumbers = len(xVals) / 2 * np.array(range(fftSize // 2 + 1)) * dWavenumber / (fftSize // 2 + 1)
        return sig, waveNumbers


    def getAutoCorrelation(self, isAutocorrMinSub: bool, stopIndex: int) -> Tuple[np.ndarray, np.ndarray]:
        """The autocorrelation of a signal is the covariance of a signal with a
        lagged version of itself, normalized so that the covariance at
        zero-lag is equal to 1.0 (c[0] = 1.0).  The same process without
        normalization is the autocovariance.

        A fast method for determining the autocovariance of a signal with
        itself is to utilize fast-fourier transforms.  In this method, the
        signal is converted to the frequency domain using fft.  The
        frequency-domain signal is then convolved with itself.  The inverse
        fft is performed on this self-convolution, yielding the
        autocorrelation.

        In this instance, the autocorrelation is determined for a series of
        lags, Z. Z is equal to [-P+1:P-1], where P is the quantity of
        measurements in each signal (the quantity of wavenumbers).  Thus, the
        quantity of lags is equal to (2*P)-1.  The fft process is fastest
        when performed on signals with a length equal to a power of 2.  To
        take advantage of this property, a Z-point fft is performed on the
        signal, where Z is a number greater than (2*P)-1 that is also a power
        of 2."""
        fftSize = int(2 ** (np.ceil(np.log2((2 * len(
            self.wavenumbers)) - 1))))  # This is the next size of fft that is  at least 2x greater than is needed but is a power of two. Results in interpolation, helps amplitude accuracy and fft efficiency.

        # Determine the fft for each signal.  The length of each signal's fft
        # will be fftSize.
        cubeFft = np.fft.rfft(self.data, n=fftSize, axis=2)

        # Determine the ifft of the cubeFft.  The resulting ifft of each signal
        # will be of length fftSize..
        cubeAutocorr = np.fft.irfft(np.abs(cubeFft) ** 2, axis=2)  # This is the autocovariance.
        # Obtain only the lags desired.
        # Then, normalize each autocovariance so the value at zero-lags is 1.
        cubeAutocorr = cubeAutocorr[:, :, :len(self.wavenumbers)]
        cubeAutocorr /= cubeAutocorr[:, :, 0, np.newaxis]

        # In some instances, minimum subtraction is desired.  In this case,
        # determine the minimum of each signal and subtract that value from
        # each value in the signal.
        if isAutocorrMinSub:
            cubeAutocorr -= cubeAutocorr.min()

        # Convert the lags from units of indices to wavenumbers.
        lags = np.array(self.wavenumbers) - min(self.wavenumbers)

        # Square the lags. This is how it is in the paper. I'm not sure why though.
        lagsSquared = lags ** 2

        # Before taking the log of the autocorrelation, zero values must be
        # modified to prevent outputs of "inf" or "-inf".
        cubeAutocorr[cubeAutocorr == 0] = 1e-323

        # Obtain the log of the autocorrelation.
        cubeAutocorrLog = np.log(cubeAutocorr)

        # A first-order polynomial fit is determined between lagsSquared and
        # and cubeAutocorrLog.  This fit is to be performed only on the first
        # linear-portion of the lagsSquared vs. cubeAutocorrLog relationship.
        # The index of the last point to be used is indicated by stopIndex.
        lagsSquared = lagsSquared[:stopIndex]
        cubeAutocorrLog = cubeAutocorrLog[:, :, :stopIndex]
        cubeAutocorrLog = np.moveaxis(cubeAutocorrLog, 2, 0)
        cubeAutocorrLog = cubeAutocorrLog.reshape(
            (cubeAutocorrLog.shape[0], cubeAutocorrLog.shape[1] * cubeAutocorrLog.shape[2]))

        # Determine the first-order polynomial fit for each cubeAutocorrLag.
        V = np.stack([np.ones(lagsSquared.shape), lagsSquared])
        V = V.T
        M = np.matmul(V, np.linalg.pinv(V))
        cubeLinear = np.matmul(M, cubeAutocorrLog)
        cubeSlope = (cubeLinear[1, :] - cubeLinear[0, :]) / (lagsSquared[1] - lagsSquared[0])
        cubeSlope = cubeSlope.reshape(self.data.shape[0], self.data.shape[1])
        # -- Coefficient of Determination
        # Obtain the mean of the observed data
        meanObserved = cubeAutocorrLog.mean(axis=0)
        # Obtain the regression sum of squares.
        ssReg = ((cubeLinear - meanObserved) ** 2).sum(axis=0)
        # Obtain the residual sum of squares.
        ssErr = ((cubeAutocorrLog - cubeLinear) ** 2).sum(axis=0)
        # Obtain the total sume of squares.
        ssTot = ssReg + ssErr
        # Obtain rSquared.
        rSquared = ssReg / ssTot
        rSquared = rSquared.reshape(self.data.shape[0], self.data.shape[1])

        cubeSlope = cubeSlope.astype(self.data.dtype)#Make sure to to upscale precision
        rSquared = rSquared.astype(self.data.dtype)
        return cubeSlope, rSquared

    @classmethod
    def fromHdfDataset(cls, dataset: h5py.Dataset):
        """
        Load the KCube object from an `h5py.Dataset` in an HDF5 file

        Args:
            dataset: The `h5py.Dataset` that the KCube data is stored in.
        Returns:
            KCube: A new instance of this class."""
        arr, index = cls.decodeHdf(dataset)
        return cls(arr, index)

    def __add__(self, other):
        ret = self._add(other)
        return KCube(ret, self.wavenumbers, metadata=self.metadata)

    def __sub__(self, other):
        ret = self._sub(other)
        return KCube(ret, self.wavenumbers, metadata=self.metadata)

    def __mul__(self, other):
        ret = self._mul(other)
        return KCube(ret, self.wavenumbers, metadata=self.metadata)

    def __truediv__(self, other):
        ret = self._truediv(other)
        return KCube(ret, self.wavenumbers, metadata=self.metadata)


class FluorescenceImage:
    """
    Represents a fluorescence image taken by the PWS acquisition software.

    Args:
        data: A 2D array of image data.
        md: The metadata object associated with this image.
    """
    def __init__(self, data: np.ndarray, md: pwsdtmd.FluorMetaData):
        self.data = data
        self.metadata = md

    @classmethod
    def fromTiff(cls, directory: str, acquisitionDirectory: Optional[pwsdtmd.AcqDir] = None) -> FluorescenceImage:
        """
        Load an image from a TIFF file.

        Args:
            directory: The path to the folder containing the TIFF file.
            acquisitionDirectory: The `AcqDir` object associated with this acquisition.

        Returns:
            A new instanse of `FluorescenceImage`.
        """
        md = pwsdtmd.FluorMetaData.fromTiff(directory, acquisitionDirectory) #This will raise an error if the folder isn't valid
        return cls.fromMetadata(md)

    @classmethod
    def fromMetadata(cls, md: pwsdtmd.FluorMetaData, lock: mp.Lock = None) -> FluorescenceImage:
        """
        Load an image from the metadata object.

        Args:
            md: The metadata object to load the image from.

        Returns:
            A new instance of `FluorescenceImage`.
        """
        path = os.path.join(md.filePath, pwsdtmd.FluorMetaData.FILENAME)
        if lock is not None:
            lock.acquire()
        try:
            img = tf.TiffFile(path)
        finally:
            if lock is not None:
                lock.release()
        return cls(img.asarray(), md)

    def toTiff(self, directory: str):
        """
        Save this object to a TIFF file.

        Args:
            directory: The path to the folder to save the new file to.
        """
        with open(os.path.join(directory, pwsdtmd.FluorMetaData.FILENAME), 'wb') as f:
            tf.imsave(f, self.data)
        with open(os.path.join(directory, pwsdtmd.FluorMetaData.MDPATH), 'w') as f:
            json.dump(self.metadata, f)

class _FFTHelper:
    class Normalization(Enum):
        POWER = 1
        AMPLITUDE = 2

    @staticmethod
    def getFFTMagnitude(data: np.ndarray, useHannWindow: bool = False, normalization: Normalization = Normalization.POWER):
        """
        Apply windowing, calculate FFT and normalize FFT for the last axis of a real-valued numpy array.

        Args:
            data: A numpy array. The FFT will be calculated along the last axis of the array. The values of this array must be real.
            useHannWindow: If True then a Hann window will be applied to the data before the FFT and the proper normalization will be applied.
            normalization:  When windowing is used the FFT must be normalized using one of two normalizations. "Amplitude" normalization will maintain
                the peak height of detected frequencies but will not preserve the total area under the curve which is asssociated with the energy/power of the signal.
                "Power" normalization will preserve the total area under the curve (important when calculating RMS from an OPD signal) but the amplitudes of detected
                frequencies will generally decrease due to the widened bandwidth associated with windowing.

        Returns:
            A numpy array with the same number of dimensions as `data`. The last axis of the array will be the magnitude of the FFT of the along the last
                axis of the `data` array. Note that the length of the last axis will be longer than the last axis of the `data` array due to FFT interpolation.
        """
        dataLength = data.shape[-1]
        fftSize = int(2 ** (np.ceil(np.log2((2 * dataLength) - 1))))  # This is the next size of fft that is  at least 2x greater than is needed but is a power of two. Results in interpolation, helps amplitude accuracy and fft efficiency.
        fftSize *= 2  # We double the fftsize for even more iterpolation. Not sure why, but that's how it was done in the original matlab code.
        if useHannWindow:  # if hann window checkbox is selected, create hann window
            w = np.hanning(dataLength)  # Hanning window
        else:
            w = np.ones((dataLength))  # Create unity window

        # Calculate the Fourier Transform of the signal multiplied by Hann window
        fft = np.fft.rfft(data * w, n=fftSize, axis=data.ndim-1)
        fft = np.abs(fft)  # We're only interested in the magnitude.
        # Normalize the FFT by the quantity of wavelengths.
        fft /= dataLength

        # by multiplying by Hann window we reduce the total power and amplitude of the signal. To account for that,
        if normalization is _FFTHelper.Normalization.POWER:
            fft *= np.sqrt(len(w) / np.sum(w ** 2)) # Correct the signal so the true power (area under curve) is preserved. This will prevent windowing from affecting integration of RMS but the amplitude of each frequency will be reduced https://dsp.stackexchange.com/questions/47598/does-windowing-affect-parsevals-theorem
        elif normalization is _FFTHelper.Normalization.AMPLITUDE:
            fft *= len(w) / np.sum(w)  # Correct amplitude scaling error caused by windowing. Does not preserve energy of signal though. https://www.mathworks.com/matlabcentral/answers/372516-calculate-windowing-correction-factor
        else:
            raise ValueError(f"{normalization} is not a valid normalization.")
        return fft
