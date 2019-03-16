import numpy as np

from pwspy.analysis.analysisResults import AbstractAnalysisResults
from pwspy.analysis.compilation.compilerSettings import CompilerSettings
from pwspy.analysis.compilation.roiCompilationResults import RoiAnalysisResults
from pwspy.imCube.otherClasses import Roi


class RoiCompiler:
    def __init__(self, settings: CompilerSettings):
        self._settings = settings

    def run(self, results: AbstractAnalysisResults, roi: Roi) ->RoiAnalysisResults:
            reflectance = self._avgOverRoi(roi, results.meanReflectance)
            rms = self._avgOverRoi(roi, results.rms)
            polynomialRms = self._avgOverRoi(roi, results.polynomialRms)
            autoCorrelationSlope = self._avgOverRoi(roi, results.autoCorrelationSlope,
                                                         condition=np.logical_and(results.rSquared > 0.9,
                                                                                  results.autoCorrelationSlope < 0))
            rSquared = self._avgOverRoi(roi, results.rSquared)
            ld = self._avgOverRoi(roi, results.ld)
            opd = results.opd[roi[:, :, None]].mean(axis=(0,1))
            opdIndex = results.opdIndex

            spectra, _ = results.reflectance.getMeanSpectra(roi)[0]
            meanRms = spectra.std()
            varRatio = meanRms**2 / (results.rms[roi.data]**2).mean()
            return RoiAnalysisResults(
                reflectance=reflectance,
                rms=rms,
                polynomialRms=polynomialRms,
                autoCorrelationSlope=autoCorrelationSlope,
                rSquared=rSquared,
                ld=ld,
                opd=opd,
                opdIndex=opdIndex,
                varRatio=varRatio)


    @staticmethod
    def _avgOverRoi(roi: Roi, arr: np.ndarray, condition: np.ndarray = None) -> float:
        if condition:
            return arr[np.logical_and(roi.data, condition)].mean()
        else:
            return arr[roi.data].mean()