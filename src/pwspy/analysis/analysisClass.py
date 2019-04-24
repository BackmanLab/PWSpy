# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 23:10:35 2019

@author: Nick
"""
from abc import ABC, abstractmethod
from typing import List, Tuple

import numpy as np
import scipy.signal as sps
from pwspy import ImCube, KCube, ExtraReflectanceCube
from pwspy.analysis import warnings
from pwspy.utility import reflectanceHelper
from pwspy.moduleConsts import Material
from . import AnalysisSettings, AnalysisResults


class AbstractAnalysis(ABC):
    @abstractmethod
    def __init__(self, settings: AnalysisSettings):
        """Does all of the one-time tasks needed to start running an analysis. e.g. prepare the reference, load the extrareflection cube, etc."""
        self.settings = settings

    @abstractmethod
    def run(self, cube) -> AnalysisResults:
        """Given an ImCube to analyze this function returns an instanse of AnalysisResults. In the PWSAnalysisApp this function is run in parallel by the AnalysisManager."""
        pass


class LegacyAnalysis(AbstractAnalysis):
    """An analysis without Extra reflection subtraction."""
    indexOpdStop = 100

    def __init__(self, settings: AnalysisSettings, ref: ImCube):
        assert ref.isCorrected()
        super().__init__(settings)
        ref.normalizeByExposure()
        self.ref = ref

    def run(self, cube: ImCube) -> Tuple[AnalysisResults, List[warnings.AnalysisWarning]]:
        assert cube.isCorrected()
        warns = []
        cube = self._normalizeImCube(cube)
        interval = (max(cube.wavelengths) - min(cube.wavelengths)) / (len(cube.wavelengths) - 1)# Wavelength interval. We are assuming equally spaced wavelengths here
        cube.data = self._filterSignal(cube.data, 1/interval)
        # The rest of the analysis will be performed only on the selected wavelength range.
        cube = cube.selIndex(self.settings.wavelengthStart, self.settings.wavelengthStop)
        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)
        warns.append(warnings.checkMeanReflectance(reflectance))
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
            opd, xvalOpd = cube.getOpd(self.settings.useHannWindow, self.indexOpdStop)
            ld = self._calculateLd(rms, slope)
        else:
            rmsPoly = slope = rSquared = opd = xvalOpd = ld = None

        results = AnalysisResults(
            meanReflectance=reflectance,
            reflectance=cube,
            rms=rms,
            polynomialRms=rmsPoly,
            autoCorrelationSlope=slope,
            rSquared=rSquared,
            opd=opd,
            opdIndex=xvalOpd,
            ld=ld,
            settings=self.settings,
            imCubeIdTag=cube.idTag,
            referenceIdTag=self.ref.idTag,
            extraReflectionTag=None,)

        return results, warns

    def _normalizeImCube(self, cube: ImCube) -> ImCube:
        cube.normalizeByExposure()
        cube.normalizeByReference(self.ref)
        return cube

    def _filterSignal(self, data: np.ndarray, sampleFreq: float):
        b, a = sps.butter(self.settings.filterOrder, self.settings.filterCutoff, fs=sampleFreq)
        return sps.filtfilt(b, a, data, axis=2)

    # -- Polynomial Fit
    def _fitPolynomial(self, cube: KCube):
        order = self.settings.polynomialOrder
        flattenedData = cube.data.reshape((cube.data.shape[0] * cube.data.shape[1], cube.data.shape[2]))
        # Flatten the array to 2d and put the wavenumber axis first.
        flattenedData = np.rollaxis(flattenedData, 1)
        # make an empty array to hold the fit values.
        cubePoly = np.zeros(flattenedData.shape)
        # At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
        polydata = np.polyfit(cube.wavenumbers, flattenedData, order)
        for i in range(order + 1):
            # Populate cubePoly with the fit values.
            cubePoly += (np.array(cube.wavenumbers)[:, np.newaxis] ** i) * polydata[i, :]
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


class Analysis(LegacyAnalysis):
    def __init__(self, settings: AnalysisSettings, ref: ImCube, extraReflectance: ExtraReflectanceCube):
        super().__init__(settings, ref)
        ref.filterDust(.75)  # Apply a blur to filter out dust particles #TODO this is in microns. I have no idea what the radius should actually be.

        theoryR = reflectanceHelper.getReflectance(settings.referenceMaterial, Material.Glass, index=ref.wavelengths)[None, None, :]
        I0 = ref.data / (theoryR + extraReflectance.data) # I0 is the intensity of the illumination source, reconstructed in units of `counts`. this is an inversion of our assumption that reference = I0*(referenceReflectance + extraReflectance)
        Iextra = extraReflectance.data * I0  # converting extraReflectance to the extra reflection in units of counts
        ref = ref - Iextra  # remove the extra reflection from our data
        ref = ref / theoryR  # now when we normalize by our reference we will get a result in units of physical reflectrance rather than arbitrary units.
        self.ref = ref
        self.extraReflection = Iextra

    def run(self, cube: ImCube) -> Tuple[AnalysisResults, List[warnings.AnalysisWarning]]:
        results, warns = super().run(cube)
        results.extraReflectionTag = self.extraReflection.idTag
        return results, warns

    def _normalizeImCube(self, cube: ImCube) -> ImCube:
        cube.normalizeByExposure()
        cube.subtractExtraReflection(self.extraReflection)
        cube.normalizeByReference(self.ref)
        return cube

