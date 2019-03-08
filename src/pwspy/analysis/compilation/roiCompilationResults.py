from dataclasses import dataclass

import numpy as np

@dataclass
class ROIAnalysisResults:
        roi = roi
        reflectance: float
        rms: float
        polynomialRms: float
        autoCorrelationSlope: float
        rSquared: float
        ld: float
        opd: np.ndarray
        xvalOpd

