import numpy as np

from pwspy.analysis.analysisResults import AbstractAnalysisResults
from pwspy.analysis.compilation.compilerSettings import CompilerSettings
from pwspy.imCube.otherClasses import Roi


class RoiCompiler:
    def __init__(self, settings: CompilerSettings):
        self._settings = settings

    def run(self, results: AbstractAnalysisResults, roi: np.ndarray):
            assert len(roi.shape) == 2
            self.roi = roi
            self.reflectance = self._avgOverRoi(roi, results.reflectance)
            self.rms = self._avgOverRoi(roi, results.rms)
            self.polynomialRms = self._avgOverRoi(roi, results.polynomialRms)
            self.autoCorrelationSlope = self._avgOverRoi(roi, results.autoCorrelationSlope,
                                                         condition=np.logical_and(results.rSquared > 0.9,
                                                                                  results.autoCorrelationSlope < 0))
            self.rSquared = self._avgOverRoi(roi, results.rSquared)
            self.ld = self._avgOverRoi(roi, results.ld)
            self.opd = results.opd[roi[:, :, None]].mean(axis=(0,1))
            self.opdIndex = results.opdIndex
            # TODO calculate the mean roi spectra ratio, maybe we should be saving the whole normalized cube

    @staticmethod
    def _avgOverRoi(roi: Roi, arr: np.ndarray, condition: np.ndarray = None) -> float:
        if condition:
            return arr[np.logical_and(roi, condition)].mean()
        else:
            return arr[roi].mean()