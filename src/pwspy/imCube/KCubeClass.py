# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:54:29 2019

@author: Nick
"""
from typing import Tuple

from .ICBaseClass import ICBase
from .ImCubeClass import ImCube
from .ICMetaDataClass import ICMetaData
import numpy as np
import scipy.interpolate as spi
import copy


class KCube(ICBase):
    """A class representing an ImCube after being transformed from being described in terms of wavelength in to
    wavenumber (k-space)."""

    def __init__(self, data: np.ndarray, wavenumbers: Tuple[float], metadata: ICMetaData = None):
        self.metadata = metadata #Just saving a reference to the original imcube in case we want to reference it.
        ICBase.__init__(self, data, wavenumbers, dtype=np.float32)

    @classmethod
    def fromImCube(cls, cube: ImCube):
        # Convert to wavenumber and reverse the order so we are ascending in order.
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
    def wavenumbers(self):
        return self.index

    def getOpd(self, isHannWindow: bool, indexOpdStop: int = None, mask=None):
        fftSize = int(2 ** (np.ceil(np.log2((2 * len(
            self.wavenumbers)) - 1))))  # %This is the next size of fft that is  at least 2x greater than is needed but is a power of two. Results in interpolation, helps amplitude accuracy and fft efficiency.
        fftSize *= 2  # We double the fftsize for even more iterpolation. Not sure why, but that's how it was done in matlab.
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
        maxOpd = 2 * np.pi / (self.wavenumbers[1] - self.wavenumbers[0])
        dOpd = maxOpd / len(self.wavenumbers)
        xVals = len(self.wavenumbers) / 2 * np.array(range(fftSize // 2 + 1)) * dOpd / (fftSize // 2 + 1)
        xVals = xVals[:indexOpdStop]

        opd = opd.astype(self.data.dtype) #Make sure to upscale precision
        xVals = xVals.astype(self.data.dtype)
        return opd, xVals

    def getAutoCorrelation(self, isAutocorrMinSub: bool, stopIndex: int):
        # The autocorrelation of a signal is the covariance of a signal with a
        # lagged version of itself, normalized so that the covariance at
        # zero-lag is equal to 1.0 (c[0] = 1.0).  The same process without
        # normalization is the autocovariance.
        #
        # A fast method for determining the autocovariance of a signal with
        # itself is to utilize fast-fourier transforms.  In this method, the
        # signal is converted to the frequency domain using fft.  The
        # frequency-domain signal is then convolved with itself.  The inverse
        # fft is performed on this self-convolution, yielding the
        # autocorrelation.
        #
        # In this instance, the autocorrelation is determined for a series of
        # lags, Z. Z is equal to [-P+1:P-1], where P is the quantity of
        # measurements in each signal (the quantity of wavenumbers).  Thus, the
        # quantity of lags is equal to (2*P)-1.  The fft process is fastest
        # when performed on signals with a length equal to a power of 2.  To
        # take advantage of this property, a Z-point fft is performed on the
        # signal, where Z is a number greater than (2*P)-1 that is also a power
        # of 2.
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
