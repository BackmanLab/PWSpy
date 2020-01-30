from __future__ import annotations

from typing import Union


from ._ICBaseClass import ICRawBase
import numpy as np
import multiprocessing as mp
import os
import tifffile as tf
import typing
if typing.TYPE_CHECKING:
    pass
from .._metadata import DynMetaData


class DynCube(ICRawBase):
    """A class representing a single acquisition of PWS Dynamics. In which the wavelength is held constant and the 3rd
    dimension of the data is time rather than wavelength. This can be analyzed to reveal information about diffusion rate.
    Contains methods for loading and saving to multiple formats as well as common operations used in analysis."""
    def __init__(self, data, metadata: DynMetaData, dtype=np.float32):
        assert isinstance(metadata, DynMetaData)
        super().__init__(data, metadata, metadata.times, dtype=dtype)

    @property
    def times(self):
        """Unlike PWS where we operate along the dimension of wavelength, in dynamics we operate along the dimension of time."""
        return self.index

    @classmethod
    def fromMetadata(cls, meta: DynMetaData, lock: mp.Lock = None) -> DynCube:
        if meta.fileFormat == DynMetaData.FileFormats.Tiff:
            return cls.fromTiff(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat == DynMetaData.FileFormats.RawBinary:
            return cls.fromOldPWS(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat is None:
            return cls.loadAny(meta.filePath, metadata=meta, lock=lock)
        else:
            raise TypeError("Invalid FileFormat")

    @classmethod
    def loadAny(cls, directory: str, metadata: DynMetaData = None, lock: mp.Lock = None):
        try:
            return DynCube.fromTiff(directory, metadata=metadata, lock=lock)
        except:
            try:
                return DynCube.fromOldPWS(directory, metadata=metadata, lock=lock)
            except:
                raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory, metadata: DynMetaData = None,  lock: mp.Lock = None):
        """Loads from the file format that was saved by the all-matlab version of the Basis acquisition code.
        Data was saved in raw binary to a file called `image_cube`. Some metadata was saved to .mat files called
        `info2` and `info3`."""
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = DynMetaData.fromOldPWS(directory)
            with open(os.path.join(directory, 'image_cube'), 'rb') as f:
                data = np.frombuffer(f.read(), dtype=np.uint16)
            data = data.reshape((metadata._dict['imgHeight'], metadata._dict['imgWidth'], len(metadata.times)), order='F')
        finally:
            if lock is not None:
                lock.release()
        data = data.copy(order='C')
        return cls(data, metadata)

    @classmethod
    def fromTiff(cls, directory, metadata: DynMetaData = None, lock: mp.Lock = None):
        """Load a dyanmics acquisition from a tiff file. if the metadata for the acquisition has already been loaded then you can provide
        is as the `metadata` argument to avoid loading it again. the `lock` argument is an optional place to provide a multiprocessing.Lock
        which can be used when multiple files in parallel to avoid giving the hard drive too many simultaneous requests, this is probably not necessary."""
        if lock is not None:
            lock.acquire()
        try:
            if metadata is None:
                metadata = DynMetaData.fromTiff(directory)
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
        if self._hasBeenNormalizedByReference:
            raise Exception("This cube has already been normalized by a reference.")
        if not self.isCorrected():
            print("Warning: This cube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not self.isExposureNormalized():
            print("Warning: This cube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        if isinstance(reference, DynCube):
            if not reference.isCorrected():
                print("Warning: The reference cube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
            if not reference.isExposureNormalized():
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
        self._hasBeenNormalizedByReference = True

    def subtractExtraReflection(self, extraReflection: np.ndarray):
        assert self.data.shape[:2] == extraReflection.shape
        if not self._hasBeenNormalizedByExposure:
            raise Exception("This DynCube has not yet been normalized by exposure. are you sure you want to normalize by exposure?")
        if not self._hasExtraReflectionSubtracted:
            self.data = self.data - extraReflection[:, :, None]
            self._hasExtraReflectionSubtracted = True
        else:
            raise Exception("The DynCube has already has extra reflection subtracted.")

    def selIndex(self, start, stop) -> DynCube:
        ret = super().selIndex(start, stop)
        md = self.metadata
        md._dict['times'] = ret.index
        return DynCube(ret.data, md)

    def getAutocorrelation(self) -> np.ndarray:
        """Returns the autocorrelation function of dynamics data along the time axis"""
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
