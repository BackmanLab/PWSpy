from typing import Optional

import numpy as np


class AnalysisWarning:
    def __init__(self, shortMsg: str, longMsg: str):
        self.longMsg = longMsg
        self.shortMsg = shortMsg


def checkMeanReflectance(r: np.ndarray) -> Optional[AnalysisWarning]:
    assert len(r.shape) == 2
    avg = r.mean()
    if avg > 1.5:
        return AnalysisWarning("R > 1.5", f"Mean reflectance is {avg} (>1.5). Is something wrong with the reference?")
    else:
        return None


def checkMeanSpectraRatio(ratio: float) -> Optional[AnalysisWarning]:
    if ratio > 0.4: #TODO the upper and lower bounds here were arbitrarily chosen without any testing.
        return AnalysisWarning("Mean RMS too high", f"Ratio between variance of mean ROI spectra and mean of spectra variance in ROI is {ratio} (>0.4). This suggests that the ROI is absorbing or fluorescing, or something stranger could be happening.")
    elif ratio < 0.3:
        return AnalysisWarning("Mean RMS too low", f"Ratio between variance of mean ROI spectra and mean of spectra variance in ROI is {ratio} (<0.3). This suggests that the ROI is absorbing or fluorescing, or something stranger could be happening.")
    else:
        return None

# def checkRSquared():
#     pass

