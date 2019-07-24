from __future__ import annotations
from pwspy.dataTypes import CameraCorrection, ExtraReflectionCube
from ._ICBaseClass import ICBase
from ._ICMetaDataClass import ICMetaData
import numpy as np


class DynCube(ICBase):
    def __init__(self, data, metadata: ICMetaData, dtype=np.float32):
        assert isinstance(metadata, ICMetaData)
        self.metadata = metadata
        ICBase.__init__(self, data, self.metadata.times, dtype=dtype)
        self._hasExtraReflectionSubtracted = False
        self._hasBeenNormalized = False
        self._cameraCorrected = False
        self._hasBeenNormalizedByReference = False

    @property
    def times(self):
        return self.index

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

    def normalizeByReference(self, reference: DynCube):
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

    def isExtraReflectionSubtracted(self) -> bool:
        return self._hasExtraReflectionSubtracted

    def selIndex(self, start, stop) -> DynCube:
        ret = super().selIndex(start, stop)
        md = self.metadata
        md._dict['wavelengths'] = ret.index
        return DynCube(ret.data, md)

    def getAutocorrelation(self) -> np.ndarray:
        truncLength = 100
        F = np.fft.rfft(self.data, axis=2)
        ac = np.fft.irfft(F * np.conjugate(F), axis=2)
        return ac[:, :, :truncLength]

