# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 11:41:32 2018

@author: Nick Anthony
"""
from __future__ import annotations

import copy

import h5py
import numpy as np
import tifffile as tf
import os
import typing
if typing.TYPE_CHECKING:
    from .. import ExtraReflectionCube
from scipy.io import savemat
from .. import ICMetaData
from ._ICBaseClass import ICRawBase
import multiprocessing as mp


class ImCube(ICRawBase):
    """ A class representing a single PWS acquisition. Contains methods for loading and saving to multiple formats as
    well as common operations used in analysis."""

    def __init__(self, data, metadata: ICMetaData, dtype=np.float32):
        assert isinstance(metadata, ICMetaData)
        super().__init__(data, metadata.wavelengths, metadata, dtype=dtype)

    @property
    def wavelengths(self):
        return self.index

    @classmethod
    def loadAny(cls, directory, metadata: ICMetaData = None,  lock: mp.Lock = None):
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
    def fromOldPWS(cls, directory, metadata: ICMetaData = None,  lock: mp.Lock = None):
        """Loads from the file format that was saved by the all-matlab version of the Basis acquisition code.
        Data was saved in raw binary to a file called `image_cube`. Some metadata was saved to .mat files called
        `info2` and `info3`."""
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = ICMetaData.fromOldPWS(directory)
            with open(os.path.join(directory, 'image_cube'), 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint16)
            data = data.reshape((metadata._dict['imgHeight'], metadata._dict['imgWidth'], len(metadata.wavelengths)), order='F')
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromTiff(cls, directory, metadata: ICMetaData = None,  lock: mp.Lock = None):
        """Loads from a 3D tiff file named `pws.tif`, or in some older data `MMStack.ome.tif`. Metadata can be stored in
        the tags of the tiff file but if there is a pwsmetadata.json file found then this is preferred.
        A multiprocessing.Lock object can be passed to this function so that it will acquire a lock during the
        hard-drive intensive parts of the function. this is useful in multi-core contexts."""
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
        """Loads from the file format used at NanoCytomics. all data and metdata is contained in a .mat file."""
        path = os.path.join(directory, 'imageCube.mat')
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = ICMetaData.fromNano(directory)
            with h5py.File(path, 'r') as hf:
                data = np.array(hf['imageCube'])
                data = np.rollaxis(data, 0, 3)
                data = data.copy(order='C')
        finally:
            if lock is not None:
                lock.release()
        return cls(data, metadata)

    @classmethod
    def fromMetadata(cls, meta: ICMetaData,  lock: mp.Lock = None) -> ImCube:
        """If provided with an ICMetadata object this function will automatically select the correct file loading method
        and will return the associated ImCube."""
        assert isinstance(meta, ICMetaData)
        if meta.fileFormat == ICMetaData.FileFormats.Tiff:
            return cls.fromTiff(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == ICMetaData.FileFormats.RawBinary:
            return cls.fromOldPWS(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == ICMetaData.FileFormats.NanoMat:
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

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        """Load an Imcube from an HDF5 dataset."""
        data, index = cls._decodeHdf(d)
        md = ICMetaData.fromHdf(d)
        return cls(data, md)

    def toHDF(self, g: h5py.Group, name: str) -> None:
        """Save the ImCube to an HDF5 dataset in HDF5 group `g`"""
        g = super().toHdfDataset(g, name=name)
        d = self.metadata.encodeHdfMetadata(g[name])

    def filterDust(self, kernelRadius: float, pixelSize: float = None) -> None:
        """This method blurs the data of the ImCube along the X and Y dimensions. This is useful if the ImCube is being
        used as a reference to normalize other ImCube. It helps blur out dust adn other unwanted small features."""
        if pixelSize is None:
            pixelSize = self.metadata.pixelSizeUm
            if pixelSize is None:
                raise ValueError("ImCube Metadata does not have a `pixelSizeUm` saved. please manually specify pixel size. use pixelSize=1 to make `kernelRadius in units of pixels.")
        super().filterDust(kernelRadius, pixelSize)

    def normalizeByReference(self, reference: ICRawBase):
        """Normalize the raw data of this data cube by a reference cube to result in data representing
        arbitrarily scaled reflectance."""
        if self._hasBeenNormalizedByReference:
            raise Exception("This ImCube has already been normalized by a reference.")
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
        if not self._hasBeenNormalizedByExposure:
            raise Exception("This ImCube has not yet been normalized by exposure. are you sure you want to normalize by exposure?")
        if not self._hasExtraReflectionSubtracted:
            self.data = self.data - extraReflection.data
            self._hasExtraReflectionSubtracted = True
        else:
            raise Exception("The ImCube has already has extra reflection subtracted.")