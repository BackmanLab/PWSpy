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

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, List

import numpy as np

from pwspy.dataTypes import Roi
from ._abstract import AbstractCompilerSettings, AbstractRoiCompilationResults, AbstractRoiCompiler
from .. import warnings
from ..pws import PWSAnalysisResults


@dataclass
class PWSCompilerSettings(AbstractCompilerSettings):
    """These settings determine which values should be processed during compilation"""
    reflectance: bool
    rms: bool
    polynomialRms: bool
    autoCorrelationSlope: bool
    rSquared: bool
    ld: bool
    opd: bool
    meanSigmaRatio: bool


@dataclass
class PWSRoiCompilationResults(AbstractRoiCompilationResults):
        cellIdTag: str
        analysisName: str
        reflectance: float
        rms: float
        polynomialRms: float
        autoCorrelationSlope: float
        rSquared: float
        ld: float
        opd: np.ndarray
        opdIndex: np.ndarray  # The x axis of a plot of opd
        varRatio: float #The ratio of signal variance of the Roi's mean spectra to the mean signal variance (rms^2) of the roi. should be between 0 and 1.


class PWSRoiCompiler(AbstractRoiCompiler):
    def __init__(self, settings: PWSCompilerSettings):
        super().__init__(settings)

    def run(self, results: PWSAnalysisResults, roi: Roi) -> Tuple[PWSRoiCompilationResults, List[warnings.AnalysisWarning]]:
        warns = []
        reflectance = self._avgOverRoi(roi, results.meanReflectance) if self.settings.reflectance else None
        rms = self._avgOverRoi(roi, results.rms) if self.settings.rms else None
        if self.settings.polynomialRms:
            try:
                polynomialRms = self._avgOverRoi(roi, results.polynomialRms)
            except KeyError:
                polynomialRms = None
        else:
            polynomialRms = None

        if self.settings.autoCorrelationSlope:
            try:
                autoCorrelationSlope = self._avgOverRoi(roi, results.autoCorrelationSlope,
                    condition=np.logical_and(results.rSquared > 0.9,
                        results.autoCorrelationSlope < 0))
            except KeyError:
                autoCorrelationSlope = None
        else:
            autoCorrelationSlope = None

        if self.settings.rSquared:
            try:
                warns.append(warnings.checkRSquared(results.rSquared[roi.mask]))
                rSquared = self._avgOverRoi(roi, results.rSquared)
            except KeyError:
                rSquared = None
        else:
            rSquared = None

        if self.settings.ld:
            try:
                ld = self._avgOverRoi(roi, results.ld)
            except KeyError:
                ld = None
        else:
            ld = None

        if self.settings.opd:
            try:
                opd, opdIndex = results.opd
                opd = opd[roi.mask].mean(axis=0)
            except KeyError:
                opd = opdIndex = None
        else:
            opd = opdIndex = None

        if self.settings.meanSigmaRatio:
            try:
                spectra = results.reflectance.getMeanSpectra(roi)[0]
                meanRms = spectra.std()
                varRatio = meanRms**2 / (results.rms[roi.mask] ** 2).mean()
                warns.append(warnings.checkMeanSpectraRatio(varRatio))
            except KeyError:
                varRatio = None
        else:
            varRatio = None

        results = PWSRoiCompilationResults(
                    cellIdTag=results.imCubeIdTag,
                    analysisName=results.analysisName,
                    reflectance=reflectance,
                    rms=rms,
                    polynomialRms=polynomialRms,
                    autoCorrelationSlope=autoCorrelationSlope,
                    rSquared=rSquared,
                    ld=ld,
                    opd=opd,
                    opdIndex=opdIndex,
                    varRatio=varRatio)
        warns = [w for w in warns if w is not None]  # Strip None from warns list
        return results, warns

    @staticmethod
    def _avgOverRoi(roi: Roi, arr: np.ndarray, condition: np.ndarray = None) -> float:
        """Returns the average of arr over the ROI.
        if condition is provided then only value of arr where the condition is satisfied are included."""
        assert len(arr.shape) == 2
        if condition is not None:
            return arr[np.logical_and(roi.mask, condition)].mean()
        else:
            return arr[roi.mask].mean()
