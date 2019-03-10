from dataclasses import dataclass

import numpy as np

from pwspy.imCube.otherClasses import Roi


@dataclass(frozen=True)
class ROIAnalysisResults:
        roi: Roi
        reflectance: float
        rms: float
        polynomialRms: float
        autoCorrelationSlope: float
        rSquared: float
        ld: float
        opd: np.ndarray
        opdIndex: np.ndarray #The x axis of a plot of opd

