from typing import Tuple, List

import numpy as np

from pwspy.analysis.analysisResults import AbstractAnalysisResults
from pwspy.analysis.compilation.compilerSettings import CompilerSettings
from pwspy.analysis.compilation.roiCompilationResults import RoiAnalysisResults
from pwspy.imCube.otherClasses import Roi
from pwspy.analysis import warnings


class RoiCompiler:
    def __init__(self, settings: CompilerSettings):
        self._settings = settings

    def run(self, results: AbstractAnalysisResults, roi: Roi) -> Tuple[RoiAnalysisResults, List[warnings.AnalysisWarning]]:
        warns = []
        reflectance = self._avgOverRoi(roi, results.meanReflectance) if self._settings.reflectance else None
        rms = self._avgOverRoi(roi, results.rms) if self._settings.rms else None
        polynomialRms = self._avgOverRoi(roi, results.polynomialRms) if self._settings.polynomialRms else None
        if self._settings.autoCorrelationSlope:
            autoCorrelationSlope = self._avgOverRoi(roi, results.autoCorrelationSlope,
                                                     condition=np.logical_and(results.rSquared > 0.9,
                                                                              results.autoCorrelationSlope < 0))
        else:
            autoCorrelationSlope = None
        warns.append(warnings.checkRSquared(results.rSquared))
        rSquared = self._avgOverRoi(roi, results.rSquared) if self._settings.rSquared else None
        ld = self._avgOverRoi(roi, results.ld) if self._settings.ld else None
        if self._settings.opd:
            opd = results.opd[roi[:, :, None]].mean(axis=(0,1))
            opdIndex = results.opdIndex
        else:
            opd = opdIndex = None
        if self._settings.meanSigmaRatio:
            spectra, _ = results.reflectance.getMeanSpectra(roi)[0]
            meanRms = spectra.std()
            varRatio = meanRms**2 / (results.rms[roi.data]**2).mean()
            warns.append(warnings.checkMeanSpectraRatio(varRatio))
        else:
            varRatio = None
        results = RoiAnalysisResults(
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
        return results, warns

    @staticmethod
    def _avgOverRoi(roi: Roi, arr: np.ndarray, condition: np.ndarray = None) -> float:
        """Returns the average of arr over the ROI.
        if condition is provided then only value of arr where the condition is satisfied are included."""
        assert len(arr.shape) == 2
        if condition:
            return arr[np.logical_and(roi.data, condition)].mean()
        else:
            return arr[roi.data].mean()
        