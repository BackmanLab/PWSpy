# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 23:10:35 2019

@author: Nick Anthony
"""
from __future__ import annotations

from multiprocessing.sharedctypes import RawArray
from typing import List, Tuple

import numpy as np
import scipy.signal as sps
from pwspy.analysis._abstract import AbstractAnalysis
from pwspy.analysis import warnings
from pwspy.utility.reflection import reflectanceHelper
from pwspy.moduleConsts import Material
from . import PWSAnalysisSettings, PWSAnalysisResults
import pandas as pd

import typing

from ._analysisSettings import PWSRuntimeAnalysisSettings

if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ImCube, ExtraReflectanceCube, KCube


class PWSAnalysis(AbstractAnalysis):
    """The standard PWS analysis routine. Initialize and then `run` for as many different ImCubes as you want.
    For a given set of settings and reference you only need to instantiate one instance of this class. You can then perform `run`
    on as many data cubes as you want."""
    def __init__(self, runtimeSettings: PWSRuntimeAnalysisSettings, ref: ImCube): #TODO it would make sense to include the reference in the runtime settings too.
        from pwspy.dataTypes import ExtraReflectionCube, ExtraReflectanceCube
        assert ref.processingStatus.cameraCorrected, "Before attempting to analyze using this reference make sure that it has had camera darkcounts and non-linearity corrected for."
        super().__init__()
        extraReflectance = ExtraReflectanceCube.fromMetadata(runtimeSettings.extraReflectanceMetaData)
        settings = runtimeSettings.getSaveableSettings()
        self.settings = settings
        ref.normalizeByExposure()
        if ref.metadata.pixelSizeUm is not None: #Only works if pixel size was saved in the metadata.
            ref.filterDust(.75)  # Apply a blur to filter out dust particles. This is in microns. I'm not sure if this is the optimal value.
        if settings.referenceMaterial is None:
            theoryR = pd.Series(np.ones((len(ref.wavelengths),)), index=ref.wavelengths) # Having this as all ones effectively ignores it.
            print("Warning: Analysis ignoring reference material correction. Extra Reflection subtraction can not be performed.")
            assert extraReflectance is None, "Extra reflectance calibration relies on being provided with the theoretical reflectance of our reference."
        else:
            theoryR = reflectanceHelper.getReflectance(settings.referenceMaterial, Material.Glass, wavelengths=ref.wavelengths, NA=settings.numericalAperture)
        if extraReflectance is None:
            Iextra = ExtraReflectionCube.create(ExtraReflectanceCube(np.zeros(ref.data.shape), ref.wavelengths, ExtraReflectanceCube.ERMetadata(ref.metadata._dict, settings.numericalAperture)), theoryR, ref)  # a bogus reflection that is all zeros
            print("Warning: PWSAnalysis ignoring extra reflection")
            assert np.all(Iextra.data == 0)
        else:
            if extraReflectance.metadata.numericalAperture != settings.numericalAperture:
                print(f"Warning: The numerical aperture of your analysis does not match the NA of the Extra Reflectance Calibration. Calibration File NA: {extraReflectance.metadata.numericalAperture}. PWSAnalysis NA: {settings.numericalAperture}.")
            Iextra = ExtraReflectionCube.create(extraReflectance, theoryR, ref) #Convert from reflectance to predicted counts/ms.
        ref.subtractExtraReflection(Iextra)  # remove the extra reflection from our data#
        if not settings.relativeUnits:
            ref = ref / theoryR[None, None, :]  # now when we normalize by our reference we will get a result in units of physical reflectance rather than arbitrary units.
        self.ref = ref
        self.extraReflection = Iextra

    def run(self, cube: ImCube) -> Tuple[PWSAnalysisResults, List[warnings.AnalysisWarning]]:
        """Runs analysis on `cube` returns a list of warnings indicating abnormal results and an analyisResults object which can be saved."""
        from pwspy.dataTypes import KCube
        assert cube.processingStatus.cameraCorrected
        warns = []
        cube = self._normalizeImCube(cube)
        interval = (max(cube.wavelengths) - min(cube.wavelengths)) / (len(cube.wavelengths) - 1)  # Wavelength interval. We are assuming equally spaced wavelengths here
        cube.data = self._filterSignal(cube.data, 1/interval)
        # The rest of the analysis will be performed only on the selected wavelength range.
        cube = cube.selIndex(self.settings.wavelengthStart, self.settings.wavelengthStop)
        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)
        cube = KCube.fromImCube(cube)  # -- Convert to K-Space
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
            imCubeIdTag=cube.metadata.idTag,
            referenceIdTag=self.ref.metadata.idTag,
            extraReflectionTag=self.extraReflection.metadata.idTag)
        warns = [warn for warn in warns if warn is not None] #Filter out null values.
        return results, warns

    def _normalizeImCube(self, cube: ImCube) -> ImCube:
        cube.normalizeByExposure()
        cube.subtractExtraReflection(self.extraReflection)
        cube.normalizeByReference(self.ref)
        return cube

    def _filterSignal(self, data: np.ndarray, sampleFreq: float):
        b, a = sps.butter(self.settings.filterOrder, self.settings.filterCutoff, fs=sampleFreq)
        return sps.filtfilt(b, a, data, axis=2).astype(data.dtype)

    # -- Polynomial Fit
    def _fitPolynomial(self, cube: KCube):
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
        A1 = 0.008 # TODO Determine what these constants are. Are they still valid for the newer analysis where we are using actual reflectance rather than just normalizing to reflectance ~= 1 ?
        A2 = 4
        ld = ((A2 / A1) * fact) * (rms / (-1 * slope.reshape(rms.shape)))
        return ld

    def copySharedDataToSharedMemory(self):
        refdata = RawArray('f', self.ref.data.size)
        refdata = np.frombuffer(refdata, dtype=np.float32).reshape(self.ref.data.shape)
        np.copyto(refdata, self.ref.data)
        self.ref.data = refdata

        iedata = RawArray('f', self.extraReflection.data.size)
        iedata = np.frombuffer(iedata, dtype=np.float32).reshape(self.extraReflection.data.shape)
        np.copyto(iedata, self.extraReflection.data)
        self.extraReflection.data = iedata
