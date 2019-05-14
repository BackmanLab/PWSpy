from typing import Tuple, List

import numpy as np

from pwspy.analysis.analysisResults import AbstractAnalysisResults
from pwspy.analysis.compilation.compilerSettings import CompilerSettings
from pwspy.analysis.compilation.roiCompilationResults import RoiCompilationResults
from pwspy.imCube.otherClasses import Roi
from pwspy.analysis import warnings

#TODO add ROI Area
class RoiCompiler:
    def __init__(self, settings: CompilerSettings):
        self.settings = settings

    def run(self, results: AbstractAnalysisResults, roi: Roi) -> Tuple[RoiCompilationResults, List[warnings.AnalysisWarning]]:
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
                warns.append(warnings.checkRSquared(results.rSquared[roi.data]))
                rSquared = self._avgOverRoi(roi, results.rSquared)
            except KeyError:
                rSquared = None
        else:
            rSquared = None
        if self.settings.ld:
            try: ld = self._avgOverRoi(roi, results.ld)
            except KeyError: ld = None
        else:
            ld = None
        if self.settings.opd:
            try:
                opd = results.opd[roi.data].mean(axis=(0, 1))
                opdIndex = results.opdIndex
            except KeyError:
                opd = opdIndex = None
        else:
            opd = opdIndex = None
        if self.settings.meanSigmaRatio:
            try:
                spectra = results.reflectance.getMeanSpectra(roi)[0]
                meanRms = spectra.std()
                varRatio = meanRms**2 / (results.rms[roi.data]**2).mean()
                warns.append(warnings.checkMeanSpectraRatio(varRatio))
            except KeyError:
                varRatio = None
        else:
            varRatio = None
        results = RoiCompilationResults(
                    roi=roi,
                    analysisName=results.analysisName,
                    reflectance=reflectance,
                    rms=rms,
                    polynomialRms=polynomialRms,
                    autoCorrelationSlope=autoCorrelationSlope,
                    rSquared=rSquared,
                    ld=ld,
                    opd=opd,
                    opdIndex=opdIndex,
                    varRatio=varRatio,
                    cellIdTag=results.imCubeIdTag)
        warns = [w for w in warns if w is not None]  # Strip None from warns list
        return results, warns

    @staticmethod
    def _avgOverRoi(roi: Roi, arr: np.ndarray, condition: np.ndarray = None) -> float:
        """Returns the average of arr over the ROI.
        if condition is provided then only value of arr where the condition is satisfied are included."""
        assert len(arr.shape) == 2
        if condition is not None:
            return arr[np.logical_and(roi.data, condition)].mean()
        else:
            return arr[roi.data].mean()
