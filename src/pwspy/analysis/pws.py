from __future__ import annotations
import dataclasses
import os
from datetime import datetime
import numpy as np
import pandas as pd
from scipy import signal as sps
import multiprocessing as mp
from typing import Type, Tuple, List, Optional
from ._abstract import AbstractHDFAnalysisResults, AbstractAnalysis, AbstractAnalysisResults, AbstractAnalysisSettings, \
    AbstractRuntimeAnalysisSettings, AbstractAnalysisGroup
from . import warnings
import pwspy.dataTypes as pwsdt
from pwspy import dateTimeFormat
from pwspy.utility.misc import cached_property
from pwspy.utility.reflection import reflectanceHelper, Material


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


class PWSAnalysis(AbstractAnalysis): #TODO Handle the case where pixels are 0, mark them as nan
    """The standard PWS analysis routine. Initialize and then `run` for as many different ImCubes as you want.
    For a given set of settings and reference you only need to instantiate one instance of this class. You can then perform `run`
    on as many data cubes as you want."""
    def __init__(self, runtimeSettings: PWSRuntimeAnalysisSettings, ref: pwsdt.ImCube): #TODO it would make sense to include the reference in the runtime settings too.
        from pwspy.dataTypes import ExtraReflectanceCube
        assert ref.processingStatus.cameraCorrected, "Before attempting to analyze using this reference make sure that it has had camera darkcounts and non-linearity corrected for."
        super().__init__()
        self._initWarnings = []
        extraReflectance = ExtraReflectanceCube.fromMetadata(runtimeSettings.extraReflectanceMetadata) if runtimeSettings.extraReflectanceMetadata is not None else None
        settings = runtimeSettings.getSaveableSettings()
        self.settings = settings
        ref.normalizeByExposure()
        if ref.metadata.pixelSizeUm is not None: #Only works if pixel size was saved in the metadata.
            ref.filterDust(.75)  # Apply a blur to filter out dust particles. This is in microns. I'm not sure if this is the optimal value.
        if settings.referenceMaterial is None:
            theoryR = pd.Series(np.ones((len(ref.wavelengths),)), index=ref.wavelengths) # Having this as all ones effectively ignores it.
            self._initWarnings.append(warnings.AnalysisWarning("Ignoring reference material", "Analysis ignoring reference material correction. Extra Reflection subtraction can not be performed."))
            assert extraReflectance is None, "Extra reflectance calibration relies on being provided with the theoretical reflectance of our reference."
        else:
            theoryR = reflectanceHelper.getReflectance(settings.referenceMaterial, Material.Glass, wavelengths=ref.wavelengths, NA=settings.numericalAperture)
        if extraReflectance is None:
            Iextra = None
            self._initWarnings.append(warnings.AnalysisWarning("Ignoring extra reflection correction.", "That's all"))
        else:
            if extraReflectance.metadata.numericalAperture != settings.numericalAperture:
                self._initWarnings.append(warnings.AnalysisWarning("NA mismatch!", f"The numerical aperture of your analysis does not match the NA of the Extra Reflectance Calibration. Calibration File NA: {extraReflectance.metadata.numericalAperture}. PWSAnalysis NA: {settings.numericalAperture}."))
            Iextra = pwsdt.ExtraReflectionCube.create(extraReflectance, theoryR, ref) #Convert from reflectance to predicted counts/ms.
            ref.subtractExtraReflection(Iextra)  # remove the extra reflection from our data#
        if not settings.relativeUnits:
            ref = ref / theoryR[None, None, :]  # now when we normalize by our reference we will get a result in units of physical reflectance rather than arbitrary units.
        self.ref = ref
        self.extraReflection = Iextra

    def run(self, cube: pwsdt.ImCube) -> Tuple[PWSAnalysisResults, List[warnings.AnalysisWarning]]:
        """Runs analysis on `cube` returns a list of warnings indicating abnormal results and an analyisResults object which can be saved."""
        assert cube.processingStatus.cameraCorrected
        warns = self._initWarnings
        cube = self._normalizeImCube(cube)
        interval = (max(cube.wavelengths) - min(cube.wavelengths)) / (len(cube.wavelengths) - 1)  # Wavelength interval. We are assuming equally spaced wavelengths here
        cube.data = self._filterSignal(cube.data, 1/interval)
        # The rest of the analysis will be performed only on the selected wavelength range.
        cube = cube.selIndex(self.settings.wavelengthStart, self.settings.wavelengthStop)
        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)
        cube = pwsdt.KCube.fromImCube(cube)  # -- Convert to K-Space
        cubePoly = self._fitPolynomial(cube)
        # Remove the polynomial fit from filtered cubeCell.
        cube.data = cube.data - cubePoly

        # -- RMS
        # Obtain the RMS of each signal in the cube.
        rms = cube.data.std(axis=2)
        if not self.settings.skipAdvanced:
            # RMS - POLYFIT
            # The RMS should be calculated on the mean-subtracted polyfit. This may
            # also be accomplished by calculating the standard-deviation.
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
            ImCubeIdTag=cube.metadata.idTag,
            referenceIdTag=self.ref.metadata.idTag,
            extraReflectionTag=self.extraReflection.metadata.idTag if self.extraReflection is not None else None)
        warns = [warn for warn in warns if warn is not None]  # Filter out null values.
        return results, warns

    def _normalizeImCube(self, cube: pwsdt.ImCube) -> pwsdt.ImCube:
        cube.normalizeByExposure()
        if self.extraReflection is not None:
            cube.subtractExtraReflection(self.extraReflection)
        cube.normalizeByReference(self.ref)
        return cube

    def _filterSignal(self, data: np.ndarray, sampleFreq: float):
        b, a = sps.butter(self.settings.filterOrder, self.settings.filterCutoff, fs=sampleFreq)  # Generatre the filter coefficients
        return sps.filtfilt(b, a, data, axis=2).astype(data.dtype)  # Actually do the filtering on the data.

    # -- Polynomial Fit
    def _fitPolynomial(self, cube: pwsdt.KCube):
        order = self.settings.polynomialOrder
        flattenedData = cube.data.reshape((cube.data.shape[0] * cube.data.shape[1], cube.data.shape[2]))
        # Flatten the array to 2d and put the wavenumber axis first.
        flattenedData = np.rollaxis(flattenedData, 1)
        # make an empty array to hold the fit values.
        cubePoly = np.zeros(flattenedData.shape, dtype=cube.data.dtype)
        # At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
        polydata = np.polyfit(cube.wavenumbers, flattenedData, order)
        for i in range(order + 1):
            # Populate cubePoly with the fit values.
            cubePoly += (np.array(cube.wavenumbers)[:, np.newaxis] ** i) * polydata[order - i, :]
        cubePoly = np.moveaxis(cubePoly, 0, 1)
        cubePoly = cubePoly.reshape(cube.data.shape)  # reshape back to a cube.
        return cubePoly

    # Ld Calculation
    @staticmethod
    def _calculateLd(rms: np.ndarray, slope: np.ndarray):
        assert rms.shape == slope.shape
        k = 2 * np.pi / 0.55
        fact = 1.38 * 1.38 / 2 / k / k
        A1 = 0.008  # TODO Determine what these constants are. Are they still valid for the newer analysis where we are using actual reflectance rather than just normalizing to reflectance ~= 1 ?
        A2 = 4
        ld = ((A2 / A1) * fact) * (rms / (-1 * slope.reshape(rms.shape)))
        return ld

    def copySharedDataToSharedMemory(self):
        refdata = mp.RawArray('f', self.ref.data.size)
        refdata = np.frombuffer(refdata, dtype=np.float32).reshape(self.ref.data.shape)
        np.copyto(refdata, self.ref.data)
        self.ref.data = refdata

        if self.extraReflection is not None:
            iedata = mp.RawArray('f', self.extraReflection.data.size)
            iedata = np.frombuffer(iedata, dtype=np.float32).reshape(self.extraReflection.data.shape)
            np.copyto(iedata, self.extraReflection.data)
            self.extraReflection.data = iedata


class PWSAnalysisResults(AbstractHDFAnalysisResults):
    """A loader for analysis results that will only load them from hard disk as needed."""
    # All these cached properties stay in memory once they are loaded. It may be necessary to add a mechanism to decache them when memory is needed.

    @staticmethod
    def fields():
        return ['time', 'reflectance', 'meanReflectance', 'rms', 'polynomialRms', 'autoCorrelationSlope', 'rSquared',
                'ld', 'ImCubeIdTag', 'referenceIdTag', 'extraReflectionTag', 'settings']

    @staticmethod
    def name2FileName(name: str) -> str:
        return f'analysisResults_{name}.h5'

    @staticmethod
    def fileName2Name(fileName: str) -> str:
        return fileName.split('analysisResults_')[1][:-3]

    @classmethod
    def create(cls, settings: PWSAnalysisSettings, reflectance: pwsdt.KCube, meanReflectance: np.ndarray, rms: np.ndarray,
               polynomialRms: np.ndarray, autoCorrelationSlope: np.ndarray, rSquared: np.ndarray, ld: np.ndarray,
               ImCubeIdTag: str, referenceIdTag: str, extraReflectionTag: Optional[str]):
        #TODO check datatypes here
        d = {'time': datetime.now().strftime(dateTimeFormat),
            'reflectance': reflectance,
            'meanReflectance': meanReflectance,
            'rms': rms,
            'polynomialRms': polynomialRms,
            'autoCorrelationSlope': autoCorrelationSlope,
            'rSquared': rSquared,
            'ld': ld,
            'ImCubeIdTag': ImCubeIdTag,
            'referenceIdTag': referenceIdTag,
            'extraReflectionTag': extraReflectionTag,
            'settings': settings}
        return cls(None, d)

    @cached_property
    @clearError
    @getFromDict
    def settings(self) -> PWSAnalysisSettings:
        return PWSAnalysisSettings.fromJsonString(bytes(np.array(self.file['settings'])).decode())

    @cached_property
    @clearError
    @getFromDict
    def ImCubeIdTag(self) -> str:
        return bytes(np.array(self.file['ImCubeIdTag'])).decode()

    @cached_property
    @clearError
    @getFromDict
    def referenceIdTag(self) -> str:
        return bytes(np.array(self.file['referenceIdTag'])).decode()

    @cached_property
    @clearError
    @getFromDict
    def time(self) -> str:
        return self.file['time']

    @cached_property
    @clearError
    @getFromDict
    def reflectance(self):
        dset = self.file['reflectance']
        return pwsdt.KCube.fromHdfDataset(dset)

    @cached_property
    @clearError
    @getFromDict
    def meanReflectance(self) -> np.ndarray:
        dset = self.file['meanReflectance']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def rms(self) -> np.ndarray:
        dset = self.file['rms']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def polynomialRms(self) -> np.ndarray:
        dset = self.file['polynomialRms']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def autoCorrelationSlope(self) -> np.ndarray:
        dset = self.file['autoCorrelationSlope']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def rSquared(self) -> np.ndarray:
        dset = self.file['rSquared']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def ld(self) -> np.ndarray:
        dset = self.file['ld']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def opd(self) -> Tuple[np.ndarray, np.ndarray]:
        dset = self.file['reflectance']
        cube = pwsdt.KCube.fromHdfDataset(dset)
        opd, opdIndex = cube.getOpd(isHannWindow=False, indexOpdStop=100)
        return opd, opdIndex

    @cached_property
    @clearError
    @getFromDict
    def extraReflectionTag(self) -> str:
        return bytes(np.array(self.file['extraReflectionTag'])).decode()


class LegacyPWSAnalysisResults(AbstractAnalysisResults):
    """Allows loading of the .mat files that were used by matlab analysis code to save analysis results. Only partially implemented."""
    def __init__(self, rms: np.ndarray):
        self._dict = {}
        self._dict['rms'] = rms

    @property
    def rms(self):
        return self._dict['rms']

    @classmethod
    def create(cls):
        raise NotImplementedError

    @classmethod
    def load(cls, directory, analysisName: str):
        import scipy.io as sio
        rms = sio.loadmat(os.path.join(directory, f'{analysisName}_Rms.mat'))['cubeRms']
        return cls(rms)


@dataclasses.dataclass
class PWSAnalysisSettings(AbstractAnalysisSettings):
    """Document me!""" #TODO document
    filterOrder: int
    filterCutoff: float
    polynomialOrder: int
    extraReflectanceId: str
    referenceMaterial: Material
    wavelengthStart: int
    wavelengthStop: int
    skipAdvanced: bool
    autoCorrStopIndex: int
    autoCorrMinSub: bool  # Determines if the autocorrelation should have it's minimum subtracted from it before processing. This is mathematically nonsense but is needed if the autocorrelation has negative values in it.
    numericalAperture: float
    relativeUnits: bool #determines if reflectance (and therefore the other parameters) should be calculated in absolute units of reflectance or just relative to the reflectance of the reference image.

    FileSuffix = 'analysis'  # This is used for saving and loading to json

    def _asDict(self) -> dict:
        d = dataclasses.asdict(self)
        if self.referenceMaterial is None:
            d['referenceMaterial'] = None
        else:
            d['referenceMaterial'] = self.referenceMaterial.name  # Convert from enum to string
        return d

    @classmethod
    def _fromDict(cls, d: dict) -> PWSAnalysisSettings:
        if d['referenceMaterial'] is not None:
            d['referenceMaterial'] = Material[d['referenceMaterial']]  # Convert from string to enum
        if 'relativeUnits' not in d.keys():
            d['relativeUnits'] = None #For a while this setting was missing from the code. Allow us to still load old files.
        return cls(**d)


class PWSAnalysisGroup(AbstractAnalysisGroup):
    """This class is simply used to group together analysis classes that are compatible with eachother."""
    @staticmethod
    def settingsClass() -> Type[PWSAnalysisSettings]:
        return PWSAnalysisSettings

    @staticmethod
    def resultsClass() -> Type[PWSAnalysisResults]:
        return PWSAnalysisResults

    @staticmethod
    def analysisClass() -> Type[PWSAnalysis]:
        return PWSAnalysis



@dataclasses.dataclass
class PWSRuntimeAnalysisSettings(AbstractRuntimeAnalysisSettings):
    settings: PWSAnalysisSettings
    extraReflectanceMetadata: Optional[pwsdt.ERMetaData]

    def getSaveableSettings(self) -> PWSAnalysisSettings:
        return self.settings