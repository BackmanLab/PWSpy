from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import typing
if typing.TYPE_CHECKING:
        from pwspy.dataTypes._otherClasses import Roi


@dataclass(frozen=True)
class RoiCompilationResults:
        cellIdTag: str
        analysisName: str
        roi: Roi
        reflectance: float
        rms: float
        polynomialRms: float
        autoCorrelationSlope: float
        rSquared: float
        ld: float
        opd: np.ndarray
        opdIndex: np.ndarray  # The x axis of a plot of opd
        varRatio: float #The ratio of signal variance of the Roi's mean spectra to the mean signal variance (rms^2) of the roi. should be between 0 and 1.
        roiArea: int #the number of pixels of an ROI

