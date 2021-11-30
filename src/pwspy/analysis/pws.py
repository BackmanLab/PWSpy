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

"""
Classes used in the analysis of PWS data.

Classes
---------

.. autosummary::
    :toctree: generated/

    PWSAnalysisSettings
    PWSAnalysisResults
    PWSAnalysis


Inheritance
-------------
.. inheritance-diagram:: PWSAnalysisSettings PWSAnalysisResults PWSAnalysis
    :parts: 1

"""

from __future__ import annotations
import dataclasses
import os
import typing
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import signal as sps
import multiprocessing as mp
from typing import Tuple, List, Optional
from ._abstract import AbstractHDFAnalysisResults, AbstractAnalysis, AbstractAnalysisResults, AbstractAnalysisSettings
from . import warnings
import pwspy.dataTypes as pwsdt
from pwspy import dateTimeFormat
from pwspy.utility.reflection import reflectanceHelper, Material

__all__ = ['PWSAnalysis', 'PWSAnalysisSettings', 'PWSAnalysisResults', "LegacyPWSAnalysisResults"]


def clearError(func):
    """This decorator tries to run the original function. If the function raises a keyerror then we raise a new keyerror with a clearer message. This is intended to be used with `field` accessors of implementations
    of `AbstractHDFAnalysisResults`."""
    def newFunc(*args):
        try:
            return func(*args)
        except KeyError:
            raise KeyError(f"The analysis file does not contain a {func.__name__} item.")
    newFunc.__name__ = func.__name__  # failing to do this renaming can mess with other decorators e.g. cached_property
    return newFunc


def getFromDict(func):
    """This decorator makes it so that when the method is run we will check if our class instance has a `file` property. If not, then we will attempt to access a `dict` property which is keyed
    by the same name as our original method. Otherwide we simply run the method. This is intended for use with implementations of `AbstractHDFAnalysisResults`"""
    def newFunc(self, *args):
        if self.file is None:
            return self.dict[func.__name__]
        else:
            return func(self, *args)

    newFunc.__name__ = func.__name__
    return newFunc


class PWSAnalysis(AbstractAnalysis):
    """The standard PWS analysis routine. Initialize and then `run` for as many different PwsCubes as you want.
    For a given set of settings and reference you only need to instantiate one instance of this class. You can then perform `run`
    on as many data cubes as you want.

    Args:
        settings: The settings used for the analysis
        extraReflectance: An object used to correct for stray reflectance present in the imaging system. This can be of type:
            None: No correction will be performed.
            ERMetaData (Recommended): The metadata object referring to a calibration file for extra reflectance. It will be processed in conjunction with the reference immage to produce an ExtraReflectionCube representing the stray reflectance in units of camera counts/ms.
            ExtraReflectanceCube: Effectively identical to supplying an ERMataData object.
            ExtraReflectionCube: An object representing the stray reflection in units of counts/ms. It is up to the user to make sure that the data is scaled appropriately to match the data being analyzed.
        ref: The reference acquisition used for analysis.
    """
    def __init__(self, settings: PWSAnalysisSettings, extraReflectance: typing.Optional[typing.Union[pwsdt.ERMetaData, pwsdt.ExtraReflectanceCube, pwsdt.ExtraReflectionCube]], ref: pwsdt.PwsCube):
        from pwspy.dataTypes import ExtraReflectanceCube
        super().__init__()
        self._initWarnings = []
        self.settings = settings
        if not ref.processingStatus.cameraCorrected:
            ref.correctCameraEffects(settings.cameraCorrection)
        if not ref.processingStatus.normalizedByExposure:
            ref.normalizeByExposure()
        if ref.metadata.pixelSizeUm is not None: #Only works if pixel size was saved in the metadata.
            ref.filterDust(.75)  # Apply a blur to filter out dust particles. This is in microns. I'm not sure if this is the optimal value.
        if settings.referenceMaterial is None:
            theoryR = pd.Series(np.ones((len(ref.wavelengths),)), index=ref.wavelengths)  # Having this as all ones effectively ignores it.
            self._initWarnings.append(warnings.AnalysisWarning("Ignoring reference material", "Analysis ignoring reference material correction. Extra Reflection subtraction can not be performed."))
            assert extraReflectance is None, "Extra reflectance calibration relies on being provided with the theoretical reflectance of our reference."
        else:
            theoryR = reflectanceHelper.getReflectance(settings.referenceMaterial, Material.Glass, wavelengths=ref.wavelengths, NA=settings.numericalAperture)

        # Handle the extra reflection cube.
        if isinstance(extraReflectance, pwsdt.ERMetaData):  # Load an extraReflectanceCube and use it in conjunction with the reference to generate an extraReflectionCube
            extraReflectance = ExtraReflectanceCube.fromMetadata(extraReflectance)

        if isinstance(extraReflectance, pwsdt.ExtraReflectanceCube):  # This case will be handled if the argument was supplied as an ExtraReflectance cube or if it was supplied as ERMetaData
            if extraReflectance.metadata.numericalAperture != settings.numericalAperture:
                self._initWarnings.append(warnings.AnalysisWarning("NA mismatch!", f"The numerical aperture of your analysis does not match the NA of the Extra Reflectance Calibration. Calibration File NA: {extraReflectance.metadata.numericalAperture}. PWSAnalysis NA: {settings.numericalAperture}."))
            Iextra = pwsdt.ExtraReflectionCube.create(extraReflectance, theoryR, ref) #Convert from reflectance to predicted counts/ms for the internal reflections of the system.
        elif isinstance(extraReflectance, pwsdt.ExtraReflectionCube): # An extraReflectionCube (counts/ms rather than a reflectance percentage) has been directly provided by the user. No need to generate one from the reference.
            Iextra = extraReflectance
        elif extraReflectance is None:
            Iextra = None
            self._initWarnings.append(warnings.AnalysisWarning("Ignoring extra reflection correction.", "That's all"))
        else:
            raise TypeError(f"`extraReflectance` of type: {type(extraReflectance)} is not supported.")

        if Iextra is not None:
            ref.subtractExtraReflection(Iextra)  # remove the extra reflection from our reference data

        if not settings.relativeUnits:
            ref = ref / theoryR[None, None, :]  # now when we normalize by our reference we will get a result in units of physical reflectance rather than arbitrary units.
        self.ref = ref
        self.extraReflection = Iextra

    def run(self, cube: pwsdt.PwsCube) -> Tuple[PWSAnalysisResults, List[warnings.AnalysisWarning]]:  # Inherit docstring
        if not cube.processingStatus.cameraCorrected:
            cube.correctCameraEffects(self.settings.cameraCorrection)
        if not cube.processingStatus.normalizedByExposure:
            cube.normalizeByExposure()
        warns = self._initWarnings
        cube = self._normalizePwsCube(cube)
        interval = (max(cube.wavelengths) - min(cube.wavelengths)) / (len(cube.wavelengths) - 1)  # Wavelength interval. We are assuming equally spaced wavelengths here
        cube.data = self._filterSignal(cube.data, 1/interval)  # Used for denoising
        # The rest of the analysis will be performed only on the selected wavelength range.
        cube = cube.selIndex(self.settings.wavelengthStart, self.settings.wavelengthStop)
        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)
        cube = pwsdt.KCube.fromPwsCube(cube)  # -- Convert to K-Space
        cube.data = self._filterWavenumber(cube, self.settings.waveNumberCutoff) # This step didn't exist until after pwspy 0.2.11. Rather than denoising it is intended to filter out high opd signals.
        cubePoly = self._fitPolynomial(cube, self.settings.polynomialOrder)
        # Remove the polynomial fit from filtered cubeCell.
        cube.data = cube.data - cubePoly

        # -- RMS
        # Obtain the RMS of each signal in the cube.
        rms = cube.data.std(axis=2)
        if not self.settings.skipAdvanced:
            # RMS - POLYFIT
            # The RMS should be calculated on the mean-subtracted polyfit. This may
            # also be accomplished by calculating the standard-deviation. This is a pointless metric IMO.
            rmsPoly = cubePoly.std(axis=2)

            slope, rSquared = cube.getAutoCorrelation(self.settings.autoCorrMinSub, self.settings.autoCorrStopIndex)
            ld = self._calculateLd(rms, slope)
        else:
            rmsPoly = slope = rSquared = ld = None

        results = PWSAnalysisResults.create(
            meanReflectance=reflectance,
            reflectance=cube,
            rms=rms,
            polynomialRms=rmsPoly,
            autoCorrelationSlope=slope,
            rSquared=rSquared,
            ld=ld,
            settings=self.settings,
            imCubeIdTag=cube.metadata.idTag,
            referenceIdTag=self.ref.metadata.idTag,
            extraReflectionTag=self.extraReflection.metadata.idTag if self.extraReflection is not None else None)
        warns = [warn for warn in warns if warn is not None]  # Filter out null values.
        return results, warns

    def _normalizePwsCube(self, cube: pwsdt.PwsCube) -> pwsdt.PwsCube:
        if self.extraReflection is not None:
            cube.subtractExtraReflection(self.extraReflection)
        cube.normalizeByReference(self.ref)
        return cube

    def _filterSignal(self, data: np.ndarray, sampleFreq: float):
        if self.settings.filterCutoff is None:  # Skip filtering.
            return data
        else:
            b, a = sps.butter(self.settings.filterOrder, self.settings.filterCutoff, fs=sampleFreq)  # Generate the filter coefficients
            return sps.filtfilt(b, a, data, axis=2).astype(data.dtype)  # Actually do the filtering on the data.

    @staticmethod
    def _filterWavenumber(cube: pwsdt.KCube, cutoff: float):
        """

        Args:
            cube: A pwspy KCube
            cutoff: The cutoff frequency of the filter, in units of um (inverse wavenumber)

        Returns:
            The data after being low-pass filtered.
        """
        if cutoff is None: # skip filtering
            return cube.data
        else:
            # Wavenumber interval. We are assuming equally spaced wavenumbers here. Units: Radians/um
            interval = (max(cube.wavenumbers) - min(cube.wavenumbers)) / (len(cube.wavenumbers) - 1)

            sampleFreq =  2 * np.pi / interval # In units of um (inverse wavenumber)
            sos = sps.butter(2, cutoff, fs=sampleFreq, output='sos')
            return sps.sosfiltfilt(sos, cube.data, axis=2).astype(cube.data.dtype)

    # -- Polynomial Fit
    @staticmethod
    def _fitPolynomial(cube: pwsdt.KCube, polynomialOrder: int):
        polynomialOrder
        flattenedData = cube.data.reshape((cube.data.shape[0] * cube.data.shape[1], cube.data.shape[2]))
        # Flatten the array to 2d and put the wavenumber axis first.
        flattenedData = np.rollaxis(flattenedData, 1)
        # make an empty array to hold the fit values.
        cubePoly = np.zeros(flattenedData.shape, dtype=cube.data.dtype)
        # At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
        polydata = np.polyfit(cube.wavenumbers, flattenedData, polynomialOrder)
        for i in range(polynomialOrder + 1):
            # Populate cubePoly with the fit values.
            cubePoly += (np.array(cube.wavenumbers)[:, np.newaxis] ** i) * polydata[polynomialOrder - i, :]
        cubePoly = np.moveaxis(cubePoly, 0, 1)
        cubePoly = cubePoly.reshape(cube.data.shape)  # reshape back to a cube.
        return cubePoly

    # Ld Calculation
    @staticmethod
    def _calculateLd(rms: np.ndarray, slope: np.ndarray):
        assert rms.shape == slope.shape
        k = 2 * np.pi / 0.55
        fact = 1.38 * 1.38 / 2 / k / k
        A1 = 0.008  # My understanding is that this constant was experimentally determined. Not really sure though.
        A2 = 4
        ld = ((A2 / A1) * fact) * (rms / (-1 * slope.reshape(rms.shape)))
        return ld

    def copySharedDataToSharedMemory(self):  # Inherit docstring
        refdata = mp.RawArray('f', self.ref.data.size)  # Create an empty ctypes array of shared memory
        refdata = np.frombuffer(refdata, dtype=np.float32).reshape(self.ref.data.shape)  # Wrap the shared memory array in a numpy array and reshape back to origianl shape
        np.copyto(refdata, self.ref.data)  # Copy our PwsCubes data to the shared memory array.
        self.ref.data = refdata # Reassign the shared memory array to our PwsCube object data attribute.

        if self.extraReflection is not None:
            iedata = mp.RawArray('f', self.extraReflection.data.size)
            iedata = np.frombuffer(iedata, dtype=np.float32).reshape(self.extraReflection.data.shape)
            np.copyto(iedata, self.extraReflection.data)
            self.extraReflection.data = iedata


class NCADCPWSAnalysis(AbstractAnalysis):
    """
    This Analysis uses the ADC (adaptive dark counts) method of calibration preferred by NC rather than the ExtraReflectance
    method
    """

    def __init__(self, settings: PWSAnalysisSettings, ref: pwsdt.PwsCube):
        super().__init__()
        ref.correctCameraEffects(settings.cameraCorrection, binning=1)  # Binning isn't stored in Nano data. assume binning is 1
        self._pwsAnalysis = PWSAnalysis(settings, None, ref)
        adcSpectra = self._getADCSpectra(self._pwsAnalysis.ref)
        self._pwsAnalysis.ref.data = self._pwsAnalysis.ref.data - adcSpectra

    def run(self, cube: pwsdt.PwsCube) -> Tuple[PWSAnalysisResults, List[warnings.AnalysisWarning]]:
        if not cube.processingStatus.cameraCorrected:
            cube.correctCameraEffects(self._pwsAnalysis.settings.cameraCorrection, binning=1) # Binning isn't stored in Nano data. assume binning is 1
        if not cube.processingStatus.normalizedByExposure:
            cube.normalizeByExposure()
        adcSpectra = self._getADCSpectra(cube)
        cube.data = cube.data - adcSpectra
        return self._pwsAnalysis.run(cube)

    def copySharedDataToSharedMemory(self):
        self._pwsAnalysis.copySharedDataToSharedMemory()

    @staticmethod
    def _getADCSpectra(cube: pwsdt.PwsCube):
        adcSlice = (slice(0, 50), slice(0, 50), None)
        return cube[adcSlice].mean(axis=(0, 1))


class PWSAnalysisResults(AbstractHDFAnalysisResults):
    """A representation of analysis results. Items are loaded from disk using lazy-loading strategy and are then cached in memory."""
    # All these cached properties stay in memory once they are loaded. It may be necessary to add a mechanism to decache them when memory is needed.

    @staticmethod
    def fields():  # Inherit docstring
        return ('time', 'reflectance', 'meanReflectance', 'rms', 'polynomialRms', 'autoCorrelationSlope', 'rSquared',
                'ld', 'imCubeIdTag', 'referenceIdTag', 'extraReflectionTag', 'settings')

    @staticmethod
    def name2FileName(name: str) -> str:  # Inherit docstring
        return f'analysisResults_{name}.h5'

    @staticmethod
    def fileName2Name(fileName: str) -> str:  # Inherit docstring
        return fileName.split('analysisResults_')[1][:-3]

    @classmethod
    def create(cls, settings: PWSAnalysisSettings, reflectance: pwsdt.KCube, meanReflectance: np.ndarray, rms: np.ndarray,
               polynomialRms: np.ndarray, autoCorrelationSlope: np.ndarray, rSquared: np.ndarray, ld: np.ndarray,
               imCubeIdTag: str, referenceIdTag: str, extraReflectionTag: Optional[str]):  # Inherit docstring
        d = {'time': datetime.now().strftime(dateTimeFormat),
            'reflectance': reflectance,
            'meanReflectance': meanReflectance,
            'rms': rms,
            'polynomialRms': polynomialRms,
            'autoCorrelationSlope': autoCorrelationSlope,
            'rSquared': rSquared,
            'ld': ld,
            'imCubeIdTag': imCubeIdTag,
            'referenceIdTag': referenceIdTag,
            'extraReflectionTag': extraReflectionTag,
            'settings': settings}
        return cls(None, d)

    @AbstractHDFAnalysisResults.FieldDecorator
    def settings(self) -> PWSAnalysisSettings:
        """The settings used for the analysis"""
        return PWSAnalysisSettings.fromJsonString(bytes(np.array(self.file['settings'])).decode())

    @AbstractHDFAnalysisResults.FieldDecorator
    def imCubeIdTag(self) -> str:
        """The idtag of the acquisition that was analyzed."""
        return bytes(np.array(self.file['imCubeIdTag'])).decode()

    @AbstractHDFAnalysisResults.FieldDecorator
    def referenceIdTag(self) -> str:
        """The idtag of the acquisition that was used as a reference for normalization."""
        return bytes(np.array(self.file['referenceIdTag'])).decode()

    @AbstractHDFAnalysisResults.FieldDecorator
    def time(self) -> str:
        """The time that the analysis was performed."""
        return self.file['time']  # TODO is this a bug that it doesn't have the same string decoding as the idtag properties?

    @AbstractHDFAnalysisResults.FieldDecorator
    def reflectance(self) -> pwsdt.KCube:
        """The KCube containing the 3D reflectance data after all corrections and analysis."""
        dset = self.file['reflectance']
        return pwsdt.KCube.fromHdfDataset(dset)

    @AbstractHDFAnalysisResults.FieldDecorator
    def meanReflectance(self) -> np.ndarray:
        """A 2D array giving the reflectance of the image averaged over the full spectra."""
        dset = self.file['meanReflectance']
        return np.array(dset)

    @AbstractHDFAnalysisResults.FieldDecorator
    def rms(self) -> np.ndarray:
        """A 2D array giving the spectral variance at each posiiton in the image."""
        dset = self.file['rms']
        return np.array(dset)

    @AbstractHDFAnalysisResults.FieldDecorator
    def polynomialRms(self) -> np.ndarray:
        """A 2D array giving the variance of the polynomial fit that was subtracted from the reflectance before
        calculating RMS."""
        dset = self.file['polynomialRms']
        return np.array(dset)

    @AbstractHDFAnalysisResults.FieldDecorator
    def autoCorrelationSlope(self) -> np.ndarray:
        """A 2D array giving the slope of the ACF of the spectra at each position in the image."""
        dset = self.file['autoCorrelationSlope']
        return np.array(dset)

    @AbstractHDFAnalysisResults.FieldDecorator
    def rSquared(self) -> np.ndarray:
        """A 2D array giving the r^2 coefficient of determination for the linear fit to the logarithm of the ACF. This
        basically tells us how confident to be in the `autoCorrelationSlope`."""
        dset = self.file['rSquared']
        return np.array(dset)

    @AbstractHDFAnalysisResults.FieldDecorator
    def ld(self) -> np.ndarray:
        """A 2D array giving Ld. A parameter derived from RMS and the ACF slope."""
        dset = self.file['ld']
        return np.array(dset)

    @AbstractHDFAnalysisResults.FieldDecorator
    def opd(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        A tuple containing: `opd`: The 3D array of values, `opdIndex`: The sequence of OPD values associated with each
        2D slice along the 3rd axis of the `opd` data.
        """
        dset = self.file['reflectance']
        cube = pwsdt.KCube.fromHdfDataset(dset)
        opd, opdIndex = cube.getOpd(useHannWindow=False, indexOpdStop=100)
        return opd, opdIndex

    @AbstractHDFAnalysisResults.FieldDecorator
    def extraReflectionTag(self) -> str:
        """The `idtag` of the extra reflectance correction used."""
        return bytes(np.array(self.file['extraReflectionTag'])).decode()

    def releaseMemory(self):
        """
        The cached properties continue to stay in RAM until they are deleted, this method deletes all cached data to release the memory.
        """
        for field in self.fields():
            try:
                delattr(self, field)
            except AttributeError:
                pass  # Fields that haven't yet been loaded won't be present for deletion


class LegacyPWSAnalysisResults(AbstractAnalysisResults):
    """
    Allows loading of the .mat files that were used by the MATLAB analysis code to save analysis results.
    """
    def __init__(self, rms: np.ndarray, ld: np.ndarray, meanReflectance: np.ndarray, rSquared: np.ndarray,
                 polynomialRms: np.ndarray, autoCorrelationSlope: np.ndarray, settings: dict):
        self._dict = {
             'meanReflectance': meanReflectance,
             'rms': rms,
             'polynomialRms': polynomialRms,
             'autoCorrelationSlope': autoCorrelationSlope,
             'rSquared': rSquared,
             'ld': ld,
             'settings': settings}

    @property
    def rms(self) -> np.ndarray:
        return self._dict['rms']

    @property
    def ld(self) -> np.ndarray:
        return self._dict['ld']

    @property
    def meanReflectance(self) -> np.ndarray:
        return self._dict['meanReflectance']

    @property
    def rSquared(self) -> np.ndarray:
        return self._dict['rSquared']

    @property
    def polynomialRms(self) -> np.ndarray:
        return self._dict['polynomialRms']

    @property
    def autoCorrelationSlope(self) -> np.ndarray:
        return self._dict['autoCorrelationSlope']

    @property
    def settings(self) -> dict:
        return self._dict['settings']

    @classmethod
    def create(cls):
        """We don't allow creating new analysis results like this, just for loading legacy files."""
        raise NotImplementedError

    @classmethod
    def load(cls, directory: str, analysisName: str) -> LegacyPWSAnalysisResults:
        """
        Load an instance of this class from a directory.

        Args:
            directory: The file path to the "Cell{x}" folder containing the analysis files.
            analysisName: The name used to save the analysis files. For example if the RMS file is named "blah_Rms.mat"
                then the analysis name is "blah".

        Returns:
            A new instance of this class loaded from file.
        """
        import scipy.io as sio
        rms = sio.loadmat(os.path.join(directory, f'{analysisName}_Rms.mat'))['cubeRms']
        ld = sio.loadmat(os.path.join(directory, f'{analysisName}_Ld.mat'))['cubeLd']
        meanReflectance = sio.loadmat(os.path.join(directory, f'{analysisName}_Reflectance.mat'))['cubeReflectance']
        rSquared = sio.loadmat(os.path.join(directory, f'{analysisName}_RSquared.mat'))['cubeRSquared']
        polynomialRms = sio.loadmat(os.path.join(directory, f'{analysisName}_RmsPoly.mat'))['cubeRmsPoly']
        autoCorrelationSlope = sio.loadmat(os.path.join(directory, f'{analysisName}_Slope.mat'))['cubeSlope']
        settings_ = dict(sio.loadmat(os.path.join(directory, f"{analysisName}_parameter")))  # These settings will be entirely different from settings in the current code.
        settings = {}
        for k, v in settings_.items():
            k: str
            v: np.ndarray
            if k.startswith('__'):
                continue  # Matlab has some built in variables that are like this.
            v = v.squeeze()
            if len(v.shape) == 0:  # 0-dimensional array, scalar
                settings[k] = v[()]
            elif v.dtype.type in ('S', 'U'):
                settings[k] = str(v[0])
            elif len(v.shape) == 1:
                settings[k] = tuple(v)
            else:
                settings[k] = v
        '''
        # None of the following were saved in the old format.
        reflectance = None  # The 3D analyzed reflectaqnce was not saved in the old version.
        imCubeIdTag = None
        referenceIdTag = None
        extraReflectionTag = None
        time = None
        '''
        return cls(rms, ld, meanReflectance, rSquared, polynomialRms, autoCorrelationSlope, settings)


@dataclasses.dataclass
class PWSAnalysisSettings(AbstractAnalysisSettings):
    """These settings determine the behavior of the PWSAnalysis class.

    Attributes:
        filterOrder (int): The `order` of the buttersworth filter used for lowpass filtering.
        filterCutoff (float): The cutoff frequency of the buttersworth filter used for lowpass filtering. Frequency unit is 1/wavelength . Set to `None` to skip lowpass filtering.
        polynomialOrder (int): The order of the polynomial which will be fit to the reflectance and then subtracted before calculating the analysis results.
        extraReflectanceId (str): The `idtag` of the extra reflection used for correction. Set to `None` if extra reflectance calibration is being skipped.
        referenceMaterial (Material): The material that was being imaged in the reference acquisition
        wavelengthStart (int): The acquisition spectra will be truncated at this wavelength before analysis. Set to `None` to bypass this step
        wavelengthStop (int): The acquisition spectra will be truncated after this wavelength before analysis. Set to `None` to bypass this step
        skipAdvanced (bool): If `True` then skip analysis of the OPD and autocorrelation.
        autoCorrStopIndex (int): The autocorrelation slope will be calculated up to this number of elements. More elements is theoretically better but it severely limited by SNR.
        autoCorrMinSub (bool): If `True` then subtract the minimum of the ACF from ACF. This prevents numerical issues but doesn't actually make any sense.
        numericalAperture (float): The numerical aperture that the acquisition was imaged at.
        relativeUnits (bool): relativeUnits: If `True` then all calculation are performed such that the reflectance is 1 if it matches the reference. If `False` then we use the
            theoretical reflectance of the reference  (based on NA and reference material) to normalize our results to the actual physical reflectance of
            the sample (about 0.4% for water)
        cameraCorrection: An object describing the dark counts and non-linearity of the camera used. If the data supplied to the PWSAnalysis class has already been corrected then this
            setting will not be used. Setting this to `None` will result in the camera correcting being automatically determined based on the image files' metadata.
        waveNumberCutoff: A cutoff frequency for filtering the signal after converting from wavelength to wavenumber. In units of microns (opd). Note: To convert from depth to opd divide by 2 (because the light makes a round trip) and divide by the RI of the media (nucleus)
    """
    filterOrder: int
    filterCutoff: typing.Optional[float]
    polynomialOrder: int
    extraReflectanceId: typing.Optional[str]
    referenceMaterial: Material
    wavelengthStart: int
    wavelengthStop: int
    skipAdvanced: bool
    autoCorrStopIndex: int
    autoCorrMinSub: bool  # Determines if the autocorrelation should have it's minimum subtracted from it before processing. This is mathematically nonsense but is needed if the autocorrelation has negative values in it.
    numericalAperture: float
    relativeUnits: bool  # determines if reflectance (and therefore the other parameters) should be calculated in absolute units of reflectance or just relative to the reflectance of the reference image.
    cameraCorrection: typing.Optional[pwsdt.CameraCorrection]
    waveNumberCutoff: float

    FileSuffix = 'analysis'  # This is used for saving and loading to json

    def asDict(self) -> dict:  # Inherit docstring
        d = dataclasses.asdict(self)
        if self.referenceMaterial is None:
            d['referenceMaterial'] = None
        else:
            d['referenceMaterial'] = self.referenceMaterial.name  # Convert from enum to string
        return d

    @classmethod
    def _fromDict(cls, d: dict) -> PWSAnalysisSettings:  # Inherit docstring
        if d['referenceMaterial'] is not None:
            d['referenceMaterial'] = Material[d['referenceMaterial']]  # Convert from string to enum
        for newKey in ['relativeUnits', 'extraReflectanceId', 'cameraCorrection', 'waveNumberCutoff']:
            if newKey not in d.keys():
                d[newKey] = None #For a while these settings were missing from the code. Allow us to still load old files.
        if d['cameraCorrection'] is not None:
            d['cameraCorrection'] = pwsdt.CameraCorrection(**d['cameraCorrection'])
        return cls(**d)

    @classmethod
    def getDefaultSettingsNames(cls) -> typing.Tuple[str]:
        from . import defaultSettingsPath
        from glob import glob
        names = []
        for i in glob(os.path.join(defaultSettingsPath, '*.json')):
            if os.path.isfile(i):
                name = os.path.basename(i).split(f"_{cls.FileSuffix}.json")[0]
                names += [name]
        return tuple(names)

    @classmethod
    def loadDefaultSettings(cls, name: str) -> PWSAnalysisSettings:
        from . import defaultSettingsPath
        return cls.fromJson(defaultSettingsPath, name)

