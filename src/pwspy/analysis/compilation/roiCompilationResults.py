from dataclasses import dataclass

import numpy as np

from pwspy.imCube.otherClasses import Roi


@dataclass(frozen=True)
class RoiAnalysisResults:
        cellPath: str
        cellNumber: int
        analysisName: str
        roi: Roi
        reflectance: float
        rms: float
        polynomialRms: float
        autoCorrelationSlope: float
        rSquared: float
        ld: float
        opd: np.ndarray
        opdIndex: np.ndarray #The x axis of a plot of opd
        varRatio: float #The ratio of signal variance of the Roi's mean spectra to the mean signal variance (rms^2) of the roi. should be between 0 and 1.

