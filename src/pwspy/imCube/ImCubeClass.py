# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 11:41:32 2018

@author: Nick
"""
from __future__ import annotations

import copy

import h5py
import numpy as np
import tifffile as tf
import os
import json
from glob import glob
import typing
import numbers
from scipy.io import savemat
if typing.TYPE_CHECKING:
    from pwspy.imCube.ExtraReflectanceCubeClass import ExtraReflectionCube
from .otherClasses import CameraCorrection
from .ICBaseClass import ICBase
from .ICMetaDataClass import ICMetaData, ICFileFormats
import multiprocessing as mp

class ImCube(ICBase):
    """ A class representing a single acquisition of PWS. Contains methods for loading and saving to multiple formats as well as common operations used in analysis."""
    _cameraCorrected: bool
    _hasBeenNormalized: bool
    _hasExtraReflectionSubtracted: bool
    _hasBeenNormalizedByReference: bool

    def __init__(self, data, metadata: ICMetaData, dtype = np.float32):
        assert isinstance(metadata, ICMetaData)
        self.metadata = metadata
        ICBase.__init__(self, data, self.metadata.wavelengths, dtype=dtype)
        self._hasBeenNormalized = False  # Keeps track of whether or not we have normalized by exposure so that we don't do it twice.
        self._cameraCorrected = False
        self._hasExtraReflectionSubtracted = False
        self._hasBeenNormalizedByReference = False

    @property
    def wavelengths(self):
        return self.index

    @classmethod
    def loadAny(cls, directory, metadata: ICMetaData = None,  lock: mp.Lock = None):
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
    def fromOldPWS(cls, directory, metadata: ICMetaData = None,  lock: mp.Lock = None):
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = ICMetaData.fromOldPWS(directory)
            with open(os.path.join(directory, 'image_cube'), 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint16)
            data = data.reshape((metadata._dict['imgHeight'], metadata._dict['imgWidth'], len(metadata.wavelengths)),
                                order='F')
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromTiff(cls, directory, metadata: ICMetaData = None,  lock: mp.Lock = None):
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = ICMetaData.fromTiff(directory)
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
    def fromNano(cls, directory: str, metadata: ICMetaData = None, lock: mp.Lock = None):
        path = os.path.join(directory, 'imageCube.mat')
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = ICMetaData.fromNano(path)
            with h5py.File(path) as hf:
                data = np.array(hf['imageCube'])
                data = np.rollaxis(data, 0, 3)
                data = data.copy(order='C')
        finally:
            if lock is not None:
                lock.release()
        return cls(data, metadata)

    @classmethod
    def fromMetadata(cls, meta: ICMetaData,  lock: mp.Lock = None):
        if meta.fileFormat == ICFileFormats.Tiff:
            return cls.fromTiff(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == ICFileFormats.RawBinary:
            return cls.fromOldPWS(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == ICFileFormats.NanoMat:
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
        info2 = {'info2': np.array([m.wavelengths[0], 0, m.wavelengths[-1], m.exposure, 0, 0, 0, 0, 0, 0],
                                   dtype=object)}
        try:
            info3 = {
                'info3': np.array([m._dict['systemId'], m.exposure, m._dict['imgHeight'], m._dict['imgWidth'], 0, 0, 0, 0, 0, 0, 0, 0],
                                  dtype=object)}  # the old way
        except:
            info3 = {'info3': np.array(
                [m._dict['system'], m.exposure, self.data.shape[0], self.data.shape[1], 0, 0, 0, 0, 0, 0, 0, 0],
                dtype=object)}  # The new way
        wv = {"WV": m.wavelengths}
        savemat(os.path.join(directory, 'info2'), info2)
        savemat(os.path.join(directory, 'info3'), info3)
        savemat(os.path.join(directory, 'WV'), wv)
        self._saveImBd(directory)
        with open(os.path.join(directory, 'image_cube'), 'wb') as f:
            f.write(self.data.astype(np.uint16).tobytes(order='F'))

    def _saveImBd(self, directory):
        imbd = self.data[:, :, self.data.shape[-1] // 2]
        nimbd = imbd - np.percentile(imbd, 0.01)  # .01 percent saturation
        nimbd = nimbd / np.percentile(nimbd, 99.99)
        nimbd = (nimbd * 255).astype(np.uint8)
        im = tf.TiffWriter(os.path.join(directory, 'image_bd.tif'))
        im.save(nimbd)
        im.close()

    def toTiff(self, outpath: str, dtype=np.uint16):
        im = self.data
        im = im.astype(dtype)
        os.mkdir(outpath)
        self._saveImBd(outpath)
        with tf.TiffWriter(open(os.path.join(outpath, 'pws.tif'), 'wb')) as w:
            w.save(np.rollaxis(im, -1, 0), metadata=self.metadata._dict)
        self.metadata.metadataToJson(outpath)

    def normalizeByExposure(self):
        if not self._cameraCorrected:
            raise Exception(
                "This ImCube has not yet been corrected for camera effects. are you sure you want to normalize by exposure?")
        if not self._hasBeenNormalized:
            self.data = self.data / self.metadata.exposure
        else:
            raise Exception("The ImCube has already been normalized by exposure.")
        self._hasBeenNormalized = True

    def correctCameraEffects(self, correction: CameraCorrection = None, binning: int = None, auto: bool = False):
        """ Subtracts the darkcounts from the data. count is darkcounts per pixel. binning should be specified if it wasn't saved in the micromanager metadata."""
        if self._cameraCorrected:
            raise Exception("This ImCube has already had it's camera correction applied!")
        if auto:
            assert (correction is None and binning is None), "correction and binning arguments should not be provided if auto is True"
            binning = self.metadata.binning
            correction = self.metadata.cameraCorrection
            if binning is None: raise ValueError('Binning metadata not found. Binning must be specified in function argument.')
            if correction is None: raise ValueError('CameraCorrection metadata not found. Binning must be specified in function argument.')
        count = correction.darkCounts * binning ** 2  # Account for the fact that binning multiplies the darkcount.
        self.data = self.data - count
        if correction.linearityPolynomial is None or correction.linearityPolynomial == (1.0,):
            pass
        else:
            self.data = np.polynomial.polynomial.polyval(self.data, (0.0,) + correction.linearityPolynomial)  # The [0] is the y-intercept (already handled by the darkcount)
        self._cameraCorrected = True
        return

    def normalizeByReference(self, reference: ImCube):
        if self._hasBeenNormalizedByReference:
            raise("This ImCube has already been normalized by a reference.")
        if not self.isCorrected():
            print("Warning: This ImCube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not self.isExposureNormalized():
            print("Warning: This ImCube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        if not reference.isCorrected():
            print("Warning: The reference ImCube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not reference.isExposureNormalized():
            print("Warning: The reference ImCube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        self.data = self.data / reference.data
        self._hasBeenNormalizedByReference = True

    def subtractExtraReflection(self, extraReflection: ExtraReflectionCube):
        assert self.data.shape == extraReflection.data.shape
        if not self._hasBeenNormalized:
            raise Exception("This ImCube has not yet been normalized by exposure. are you sure you want to normalize by exposure?")
        if not self._hasExtraReflectionSubtracted:
            self.data = self.data - extraReflection.data
        else:
            raise Exception("The ImCube has already has extra reflection subtracted.")

    def isCorrected(self) -> bool:
        return self._cameraCorrected

    def isExposureNormalized(self) -> bool:
        return self._hasBeenNormalized

    def selIndex(self, start, stop) -> ImCube:
        ret = super().selIndex(start, stop)
        md = self.metadata
        md._dict['wavelengths'] = ret.index
        return ImCube(ret.data, md)

    def isExtraReflectionSubtracted(self) -> bool:
        return self._hasExtraReflectionSubtracted

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

    def __truediv__(self, other):
        ret = self._truediv(other)
        new = copy.deepcopy(self)
        new.data = ret
        return new

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        data, index = cls._decodeHdf(d)
        md = ICMetaData.fromHdf(d)
        return cls(data, md)

    def toHDF(self, g: h5py.Group, name: str) -> None:
        g = super().toHdfDataset(g, name=name)
        d = self.metadata.encodeHdfMetadata(g[name])

    def filterDust(self, kernelRadius: float, pixelSize: float = None) -> None:
        if pixelSize is None:
            pixelSize = self.metadata.pixelSizeUm
            if pixelSize is None:
                raise ValueError("ImCube Metadata does not have a `pixelSizeUm` saved. please manually specify pixel size. use pixelSize=1 to make `kernelRadius in units of pixels.")
        super().filterDust(kernelRadius, pixelSize)




# class FakeCube(ImCube):
#     def __init__(self, num: int):
#         x = y = np.arange(0, 256)
#         z = np.arange(0, 100)
#         Y, X, Z = np.meshgrid(y, x, z)
#         freq = np.random.random() / 4
#         freq2 = np.random.random() / 4
#         data = np.exp(-np.sqrt((X - X.max() / 2) ** 2 + (Y - Y.max() / 2) ** 2) / (x.max() / 4)) * (
#                 .75 + 0.25 * np.cos(freq2 * 2 * np.pi * Z)) * (0.5 + 0.5 * np.sin(freq * 2 * np.pi * X))
#         md = {'wavelengths': z + 500, 'exposure': 100, 'time': '315'}
#         super().__init__(data, md)
