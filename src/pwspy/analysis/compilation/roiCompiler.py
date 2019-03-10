import numpy as np

from pwspy.analysis.compilation.compilerSettings import CompilerSettings


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
            self.opd =
            self.xvalOpd =
            # TODO calculate the mean roi spectra ratio

    @staticmethod
    def _avgOverRoi(roi: Roi, arr: np.ndarray, condition: np.ndarray = None):
        if condition:
            return arr[np.logical_and(roi, condition)].mean()
        else:
            return arr[roi].mean()