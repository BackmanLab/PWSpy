from __future__ import annotations
import copy
import json
import multiprocessing as mp
import numbers
import os
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass
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


class ICBase:
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

    def selectLassoROI(self, displayIndex: typing.Optional[int] = None) -> np.ndarray:
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
        ax.imshow(self.data[:, :, displayIndex])
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
        from pwspy.utility.matplotlibWidgets import AxManager, PointSelector
        verts = [None]
        if displayIndex is None:
           displayIndex = self.data.shape[2]//2
        fig, ax = plt.subplots()
        ax.imshow(self.data[:, :, displayIndex])
        fig.suptitle("Close to accept ROI")
        def select(Verts, handles):
            verts[0] = Verts
        axMan = AxManager(ax)
        sel = PointSelector(axMan, onselect=select, sideLength=side)
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
        sigma = sigma / pixelSize  # convert from microns to pixels
        for i in range(self.data.shape[2]):
            self.data[:, :, i] = sp.ndimage.filters.gaussian_filter(self.data[:, :, i], sigma, mode='reflect')

    def _indicesMatch(self, other: 'ICBase') -> bool:
        """This check is performed before allowing many arithmetic operations between two data cubes. Makes sure that the Z-axis of the two cubes match."""
        return self._index == other._index

    def selIndex(self, start: float, stop: float) -> ICBase:
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

    def toHdfDataset(self, g: h5py.Group, name: str, fixedPointCompression: bool = True) -> h5py.Group:
        """
        Save the data of this class to a new HDF dataset.

            Args:
                g (h5py.Group): the parent HDF Group of the new dataset.
                name (str): the name of the new HDF dataset in group `g`.
                fixedPointCompression (bool): if True then save the data in a special 16bit fixed-point format. Testing has shown that this has a
                    maximum conversion error of 1.4e-3 percent. Saving is ~10% faster but requires only 50% the hard drive space.

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
            dset = g.create_dataset(name, data=fpData)  # , chunks=(64,64,self.data.shape[2]), compression=2)
            dset.attrs['index'] = np.array(self.index)
            dset.attrs['type'] = np.string_(f"{self.__class__.__name__}_fp") #TODO if the classes get renamed then this will break. need to use a different identifier that won't be accidentally changed
            dset.attrs['min'] = m
            dset.attrs['max'] = M
        else:
            dset = g.create_dataset(name, data=self.data)
            dset.attrs['index'] = np.array(self.index)
            dset.attrs['type'] = np.string_(self.__class__.__name__)
        return g

    @classmethod
    def decodeHdf(cls, d: h5py.Dataset) -> Tuple[np.array, Tuple[float, ...]]:
        """
        Load a new instance of ICBase from an `h5py.Dataset`

        Args:
            d: The dataset that the ICBase has been saved to

        Returns:
            A tuple containing:
                data: The 3D array of `data`
                index: A tuple containing the `index`
        """
        assert 'type' in d.attrs
        assert 'index' in d.attrs
        if d.attrs['type'].decode() == cls.__name__: #standard decoding #TODO if the classes get renamed then this will break. need to use a different identifier that won't be accidentally changed
            return np.array(d), tuple(d.attrs['index'])
        elif d.attrs['type'].decode() == f"{cls.__name__}_fp": #Fixed point decoding
            print("Decoding fixed point")
            M = d.attrs['max']
            m = d.attrs['min']
            arr = np.array(d)
            arr = arr.astype(np.float32) / (2 ** 16 - 1)
            arr *= (M - m)
            arr += m
            return arr, tuple(d.attrs['index'])
        else:
            raise TypeError(f"Got {d.attrs['type'].decode()} instead of {cls.__name__}")


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
        def fromDict(cls, d: dict) -> 'ProcessingStatus':
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
    def loadAny(cls, directory: str, metadata: pwsdtmd.DynMetaData = None, lock: mp.Lock = None):
        #TODO continue documentation from here.
        try:
            return DynCube.fromTiff(directory, metadata=metadata, lock=lock)
        except:
            try:
                return DynCube.fromOldPWS(directory, metadata=metadata, lock=lock)
            except:
                raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory, metadata: pwsdtmd.DynMetaData = None,  lock: mp.Lock = None):
        """Loads from the file format that was saved by the all-matlab version of the Basis acquisition code.
        Data was saved in raw binary to a file called `image_cube`. Some metadata was saved to .mat files called
        `info2` and `info3`."""
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = pwsdtmd.DynMetaData.fromOldPWS(directory)
            with open(os.path.join(directory, 'image_cube'), 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint16)
            data = data.reshape((metadata._dict['imgHeight'], metadata._dict['imgWidth'], len(metadata.times)), order='F')
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromTiff(cls, directory, metadata: pwsdtmd.DynMetaData = None, lock: mp.Lock = None):
        """Load a dyanmics acquisition from a tiff file. if the metadata for the acquisition has already been loaded then you can provide
        is as the `metadata` argument to avoid loading it again. the `lock` argument is an optional place to provide a multiprocessing.Lock
        which can be used when multiple files in parallel to avoid giving the hard drive too many simultaneous requests, this is probably not necessary."""
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
        should be 2D and its shape should match the first two dimensions of this DynCube."""
        if self.processingStatus.normalizedByReference:
            raise Exception("This cube has already been normalized by a reference.")
        if not self.processingStatus.cameraCorrected:
            print("Warning: This cube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not self.processingStatus.normalizedByExposure:
            print("Warning: This cube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        if isinstance(reference, DynCube):
            if not reference.processingStatus.cameraCorrected:
                print("Warning: The reference cube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
            if not reference.processingStatus.normalizedByExposure:
                print("Warning: The reference cube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
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

    def subtractExtraReflection(self, extraReflection: np.ndarray):
        assert self.data.shape[:2] == extraReflection.shape
        if not self.processingStatus.normalizedByExposure:
            raise Exception("This DynCube has not yet been normalized by exposure. are you sure you want to normalize by exposure?")
        if not self.processingStatus.extraReflectionSubtracted:
            self.data = self.data - extraReflection[:, :, None]
            self.processingStatus.extraReflectionSubtracted = True
        else:
            raise Exception("The DynCube has already has extra reflection subtracted.")

    def selIndex(self, start, stop) -> DynCube:
        ret = super().selIndex(start, stop)
        md = self.metadata
        md._dict['times'] = ret.index
        return DynCube(ret.data, md)

    def getAutocorrelation(self) -> np.ndarray:
        """Returns the autocorrelation function of dynamics data along the time axis. The ACF is calculated using fourier transforms using IFFT(FFT(data)*conj(FFT(data)))/length(data)"""
        data = self.data - self.data.mean(axis=2)[:, :, None]  # By subtracting the mean we get an ACF where the 0-lag value is the variance of the signal.
        F = np.fft.rfft(data, axis=2)
        ac = np.fft.irfft(F * np.conjugate(F), axis=2) / data.shape[2]
        return ac

    def filterDust(self, kernelRadius: float, pixelSize: float = None) -> None:
        """This method blurs the data of the cube along the X and Y dimensions. This is useful if the cube is being
        used as a reference to normalize other cube. It helps blur out dust adn other unwanted small features."""
        if pixelSize is None:
            pixelSize = self.metadata.pixelSizeUm
            if pixelSize is None:
                raise ValueError("DynCube Metadata does not have a `pixelSizeUm` saved. please manually specify pixel size. use pixelSize=1 to make `kernelRadius in units of pixels.")
        super().filterDust(kernelRadius, pixelSize)

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        """Load an Imcube from an HDF5 dataset."""
        data, index, mdDict, processingStatus = cls.decodeHdf(d)
        md = pwsdtmd.DynMetaData(mdDict, fileFormat=pwsdtmd.DynMetaData.FileFormats.Hdf)
        return cls(data, md, processingStatus=processingStatus)


class ExtraReflectanceCube(ICBase):
    """This class represents a 3D data cube of the extra reflectance in a PWS system. It's values are in units of
    reflectance (between 0 and 1). It has a `metadata` attribute which is of type ERMetaData. It also has a `data` attribute
    of numpy.ndarray type."""

    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: pwsdtmd.ERMetaData):
        assert isinstance(metadata, pwsdtmd.ERMetaData)
        if data.max() > 1 or data.min() < 0:
            print("Warning!: Reflectance values must be between 0 and 1")
        self.metadata = metadata
        ICBase.__init__(self, data, wavelengths)

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        """The wavelengths corresponding to each element along the 3rd axis of `self.data`."""
        return self.index

    @classmethod
    def fromHdfFile(cls, directory: str, name: str) -> ExtraReflectanceCube:
        """Load an ExtraReflectanceCube from an HDF5 file. `name` should be the file name, excluding the '_ExtraReflectance.h5' suffix."""
        filePath = pwsdtmd.ERMetaData.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[pwsdtmd.ERMetaData._DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    def toHdfFile(self, directory: str, name: str) -> None:
        """Save an ExtraReflectanceCube to an HDF5 file. The filename will be `name` with the '_ExtraReflectance.h5' suffix."""
        savePath = pwsdtmd.ERMetaData.dirName2Directory(directory, name)
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            self.toHdfDataset(hf)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        """Save the ExtraReflectanceCube to an HDF5 dataset. `g` should be an h5py Group or File."""
        g = super().toHdfDataset(g, pwsdtmd.ERMetaData._DATASETTAG)
        g = self.metadata.toHdfDataset(g)
        return g

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None):
        """Load the ExtraReflectanceCube from `d`, an HDF5 dataset."""
        data, index = cls.decodeHdf(d)
        md = pwsdtmd.ERMetaData.fromHdfDataset(d, filePath=filePath)
        return cls(data, index, md)

    @classmethod
    def fromMetadata(cls, md: pwsdtmd.ERMetaData):
        """Load an ExtraReflectanceCube from an ERMetaData object corresponding to an HDF5 file."""
        directory, name = pwsdtmd.ERMetaData.directory2dirName(md.filePath)
        return cls.fromHdfFile(directory, name)


class ExtraReflectionCube(ICBase):
    """This class is meant to be constructed from an ExtraReflectanceCube along with additional reference measurement
    information. Rather than being in units of reflectance (between 0 and 1) it is in the same units as the reference measurement
    that is provided with, usually counts/ms or just counts."""
    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: pwsdtmd.ERMetaData):
        super().__init__(data, wavelengths)
        self.metadata = metadata

    @classmethod
    def create(cls, reflectance: ExtraReflectanceCube, theoryR: pd.Series, reference: ImCube):
        """Construct and ExtraReflectionCube from an ExtraReflectanceCube and a reference measurement. The resulting
        ExtraReflectionCube will be in the same units as `reference`. `theoryR` should be a spectrum describing the theoretically
        expected reflectance of the reference data cube. Both `theoryR` and `reflectance` should be in units of reflectance
        (between 0 and 1)."""
        I0 = reference.data / (theoryR[None, None, :] + reflectance.data)  # I0 is the intensity of the illumination source, reconstructed in units of `counts`. this is an inversion of our assumption that reference = I0*(referenceReflectance + extraReflectance)
        data = reflectance.data * I0  # converting extraReflectance to the extra reflection in units of counts
        return cls(data, reflectance.wavelengths, reflectance.metadata)


class ImCube(ICRawBase):
    """ A class representing a single PWS acquisition. Contains methods for loading and saving to multiple formats as
    well as common operations used in analysis."""

    def __init__(self, data, metadata: pwsdtmd.ICMetaData, processingStatus: ICRawBase.ProcessingStatus=None, dtype=np.float32):
        assert isinstance(metadata, pwsdtmd.ICMetaData)
        super().__init__(data, metadata.wavelengths, metadata, processingStatus=processingStatus, dtype=dtype)

    @property
    def wavelengths(self):
        return self.index

    @classmethod
    def loadAny(cls, directory, metadata: pwsdtmd.ICMetaData = None,  lock: mp.Lock = None):
        """Attempt loading any of the known file formats."""
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
    def fromOldPWS(cls, directory, metadata: pwsdtmd.ICMetaData = None,  lock: mp.Lock = None):
        """Loads from the file format that was saved by the all-matlab version of the Basis acquisition code.
        Data was saved in raw binary to a file called `image_cube`. Some metadata was saved to .mat files called
        `info2` and `info3`."""
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = pwsdtmd.ICMetaData.fromOldPWS(directory)
            with open(os.path.join(directory, 'image_cube'), 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint16)
            data = data.reshape((metadata._dict['imgHeight'], metadata._dict['imgWidth'], len(metadata.wavelengths)), order='F')
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromTiff(cls, directory, metadata: pwsdtmd.ICMetaData = None,  lock: mp.Lock = None):
        """Loads from a 3D tiff file named `pws.tif`, or in some older data `MMStack.ome.tif`. Metadata can be stored in
        the tags of the tiff file but if there is a pwsmetadata.json file found then this is preferred.
        A multiprocessing.Lock object can be passed to this function so that it will acquire a lock during the
        hard-drive intensive parts of the function. this is useful in multi-core contexts."""
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
    def fromNano(cls, directory: str, metadata: pwsdtmd.ICMetaData = None, lock: mp.Lock = None):
        """Loads from the file format used at NanoCytomics. all data and metdata is contained in a .mat file."""
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
        """If provided with an ICMetadata object this function will automatically select the correct file loading method
        and will return the associated ImCube."""
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
        if os.path.exists(directory):
            raise OSError("The specified directory already exists.")
        os.mkdir(directory)
        m = self.metadata
        try:
            systemId = m._dict['systemId']
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
        """Save the ImCube to the standard tiff file format."""
        im = self.data
        im = im.astype(dtype)
        os.mkdir(outpath)
        self._saveThumbnail(outpath)
        with tf.TiffWriter(open(os.path.join(outpath, 'pws.tif'), 'wb')) as w:
            w.save(np.rollaxis(im, -1, 0), metadata=self.metadata._dict)
        self.metadata.metadataToJson(outpath)

    def selIndex(self, start, stop) -> ImCube:
        """Return a copy of this ImCube only within a range of wavelengths."""
        ret = super().selIndex(start, stop)
        md = copy.deepcopy(self.metadata)  # We are creating a copy of the metadata object because modifying the original metadata object can cause weird issues.
        assert md._dict is not self.metadata._dict
        md._dict['wavelengths'] = ret.index
        return ImCube(ret.data, md)

    @staticmethod
    def getMetadataClass() -> Type[pwsdtmd.ICMetaData]:
        return pwsdtmd.ICMetaData

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        """Load an Imcube from an HDF5 dataset."""
        data, index, mdDict, processingStatus = cls.decodeHdf(d)
        md = pwsdtmd.ICMetaData(mdDict, fileFormat=pwsdtmd.ICMetaData.FileFormats.Hdf)
        return cls(data, md, processingStatus=processingStatus)

    def filterDust(self, kernelRadius: float, pixelSize: float = None) -> None:
        """This method blurs the data of the ImCube along the X and Y dimensions. This is useful if the ImCube is being
        used as a reference to normalize other ImCube. It helps blur out dust adn other unwanted small features."""
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
        if self.processingStatus.normalizedByReference:
            raise Exception("This ImCube has already been normalized by a reference.")
        if not self.processingStatus.cameraCorrected:
            print("Warning: This ImCube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not self.processingStatus.normalizedByExposure:
            print("Warning: This ImCube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        if not reference.processingStatus.cameraCorrected:
            print("Warning: The reference ImCube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not reference.processingStatus.normalizedByExposure:
            print("Warning: The reference ImCube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        self.data = self.data / reference.data
        self.processingStatus.normalizedByReference = True

    def subtractExtraReflection(self, extraReflection: ExtraReflectionCube):
        assert self.data.shape == extraReflection.data.shape
        if not self.processingStatus.normalizedByExposure:
            raise Exception("This ImCube has not yet been normalized by exposure. are you sure you want to normalize by exposure?")
        if not self.processingStatus.extraReflectionSubtracted:
            self.data = self.data - extraReflection.data
            self.processingStatus.extraReflectionSubtracted = True
        else:
            raise Exception("The ImCube has already has extra reflection subtracted.")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.metadata.idTag})"


class KCube(ICBase):
    """A class representing an ImCube after being transformed from being described in terms of wavelength to
    wavenumber (k-space). Much of the analysis operated in terms of k-space."""

    def __init__(self, data: np.ndarray, wavenumbers: Tuple[float], metadata: pwsdtmd.ICMetaData = None):
        self.metadata = metadata #Just saving a reference to the original imcube in case we want to reference it.
        ICBase.__init__(self, data, wavenumbers, dtype=np.float32)

    @classmethod
    def fromImCube(cls, cube: ImCube):
        """Convert an ImCube into a KCube. Data is converted from wavelength to wavenumber (1/lambda), interpolation is
        then used to linearize the data in terms of wavenumber."""
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

    def getOpd(self, isHannWindow: bool, indexOpdStop: int = None, mask=None) -> Tuple[np.ndarray, np.ndarray]:
        fftSize = int(2 ** (np.ceil(np.log2((2 * len(self.wavenumbers)) - 1))))  # This is the next size of fft that is  at least 2x greater than is needed but is a power of two. Results in interpolation, helps amplitude accuracy and fft efficiency.
        fftSize *= 2  # We double the fftsize for even more iterpolation. Not sure why, but that's how it was done in the original matlab code.
        if isHannWindow:  # if hann window checkbox is selected, create hann window
            w = np.hanning(len(self.wavenumbers))  # Hanning window
        else:
            w = np.ones((len(self.wavenumbers)))  # Create unity window

        # Calculate the Fourier Transform of the signal multiplied by Hann window
        opd = np.fft.rfft(self.data * w[np.newaxis, np.newaxis, :], n=fftSize, axis=2)
        # Normalize the OPD by the quantity of wavelengths.
        opd = opd / len(self.wavenumbers)

        # by multiplying by Hann window we reduce the total power of signal. To account for that,
        opd = np.abs(opd / np.sqrt(np.mean(w ** 2)))

        # Isolate the desired values in the OPD.
        opd = opd[:, :, :indexOpdStop]

        if not mask is None:
            opd = opd[mask].mean(axis=0)

        # Generate the xval for the current OPD.
        dk = self.wavenumbers[1] - self.wavenumbers[0] #The interval that our linear array of wavenumbers is spaced by
        maxOpd = 2 * np.pi / dk #This is the maximum OPD value we can get with. tighter wavenumber spacing increases OPD range. units of microns
        dOpd = maxOpd / len(self.wavenumbers) #The interval we want between values in our opd vector.
        xVals = len(self.wavenumbers) / 2 * np.array(range(fftSize // 2 + 1)) * dOpd / (fftSize // 2 + 1)
        #The above line is how it was writtne in the matlab code. Couldn't it be simplified down to maxOpd * np.linspace(0, 1, num = fftSize // 2 + 1) / 2 ? I'm not sure what the 2 means though.
        xVals = xVals[:indexOpdStop]

        opd = opd.astype(self.data.dtype) #Make sure to upscale precision
        xVals = xVals.astype(self.data.dtype)
        return opd, xVals

    # @classmethod
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

    # def toImCube(self) -> ImCube:
    #     # Convert to wavenumber and reverse the order so we are ascending in order.
    #     wavelengths = (2 * np.pi) / (np.array(self.wavenumbers, dtype=np.float64) * 1e-3)[::-1]
    #     data = self.data[:, :, ::-1]
    #     # Generate evenly spaced wavelengths
    #     evenWavelengths = np.linspace(wavelengths[0], wavelengths[-1], num=len(wavelengths), dtype=np.float64)
    #     # Interpolate to the evenly spaced wavenumbers
    #     interpFunc = spi.interp1d(wavelengths, data, kind='linear', axis=2)
    #     data = interpFunc(evenWavelengths)
    #     md = copy.deepcopy(self.metadata)
    #     md['wavelengths'] = evenWavelengths.astype(np.float32)
    #     return ImCube(data, md, dtype=np.float32)

    @classmethod
    def fromHdfDataset(cls, dataset: h5py.Dataset):
        """Load the KCube object from an `h5py.Dataset` in an HDF5 file
        Args:
            dataset (h5py.Dataset): The `h5py.Dataset` that the KCube data is stored in.
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
    def __init__(self, data: np.ndarray, md: pwsdtmd.FluorMetaData):
        self.data = data
        self.metadata = md

    @classmethod
    def fromTiff(cls, directory: str, acquisitionDirectory: Optional[pwsdtmd.AcqDir] = None):
        md = pwsdtmd.FluorMetaData.fromTiff(directory, acquisitionDirectory) #This will raise an error if the folder isn't valid
        return cls.fromMetadata(md)

    @classmethod
    def fromMetadata(cls, md: pwsdtmd.FluorMetaData, lock: mp.Lock = None):
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
        with open(os.path.join(directory, pwsdtmd.FluorMetaData.FILENAME), 'wb') as f:
            tf.imsave(f, self.data)
        with open(os.path.join(directory, pwsdtmd.FluorMetaData.MDPATH), 'w') as f:
            json.dump(self.metadata, f)