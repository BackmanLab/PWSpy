from __future__ import annotations

from typing import Union


from ._ICBaseClass import ICBase, ICRawBase
from .._metadata import DynMetaData
import numpy as np
import multiprocessing as mp
import os
import tifffile as tf
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import CameraCorrection


class DynCube(ICRawBase):
    """A class representing a single acquisition of PWS Dynamics. In which the wavelength is held constant and the 3rd
    dimension of the data is time rather than wavelength. This can be analyzed to reveal information about diffusion rate.
    Contains methods for loading and saving to multiple formats as well as common operations used in analysis."""
    def __init__(self, data, metadata: DynMetaData, dtype=np.float32):
        assert isinstance(metadata, DynMetaData)
        super().__init__(data, metadata, self.metadata.times, dtype=dtype)

    @property
    def times(self):
        """Unlike PWS where we operate along the dimension of wavelength, in dynamics we operate along the dimension of time."""
        return self.index

    @classmethod
    def fromMetadata(cls, meta: DynMetaData, lock: mp.Lock = None) -> DynCube:
        if meta.fileFormat == DynMetaData.FileFormats.Tiff:
            return cls.fromTiff(meta.filePath, metadata=meta, lock=lock)
        elif meta.fileFormat is None:
            return cls.loadAny(meta.filePath, metadata=meta, lock=lock)
        else:
            raise TypeError("Invalid FileFormat")

    @classmethod
    def loadAny(cls, directory: str, metadata: DynMetaData = None, lock: mp.Lock = None):
        try:
            return DynCube.fromTiff(directory, metadata=metadata, lock=lock)
        except:
            raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromTiff(cls, directory, metadata: DynMetaData = None, lock: mp.Lock = None):
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
        if not reference.isCorrected():
            print("Warning: The reference cube has not been corrected for camera effects. This is highly reccomended before performing any analysis steps.")
        if not reference.isExposureNormalized():
            print("Warning: The reference cube has not been normalized by exposure. This is highly reccomended before performing any analysis steps.")
        if isinstance(reference, np.ndarray):
            assert len(reference.shape) == 2
            assert reference.shape[0] == self.data.shape[0]
            assert reference.shape[1] == self.data.shape[1]
            mean = reference
        elif isinstance(reference, DynCube):
            mean = reference.data.mean(axis=2)
        else:
            raise TypeError(f"`reference` must be either DynCube or numpy.ndarray, not {type(reference)}")
        self.data = self.data / mean[:, :, None]
        self._hasBeenNormalizedByReference = True

    def selIndex(self, start, stop) -> DynCube:
        ret = super().selIndex(start, stop)
        md = self.metadata
        md._dict['times'] = ret.index
        return DynCube(ret.data, md)

    def getAutocorrelation(self) -> np.ndarray:
        data = self.data - self.data.mean(axis=2) # By subtracting the mean we get and ACF where the 0-lag value is the variance of the signal.
        truncLength = 100
        F = np.fft.rfft(data, axis=2)
        ac = np.fft.irfft(F * np.conjugate(F), axis=2) / F.shape[2]
        return ac[:, :, :truncLength]

    def filterDust(self, kernelRadius: float, pixelSize: float = None) -> None:
        """This method blurs the data of the cube along the X and Y dimensions. This is useful if the cube is being
        used as a reference to normalize other cube. It helps blur out dust adn other unwanted small features."""
        if pixelSize is None:
            pixelSize = self.metadata.pixelSizeUm
            if pixelSize is None:
                raise ValueError("DynCube Metadata does not have a `pixelSizeUm` saved. please manually specify pixel size. use pixelSize=1 to make `kernelRadius in units of pixels.")
        super().filterDust(kernelRadius, pixelSize)
