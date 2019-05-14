from typing import Optional

import numpy as np


class AnalysisWarning:
    def __init__(self, shortMsg: str, longMsg: str):
        self.longMsg = longMsg
        self.shortMsg = shortMsg


def checkMeanReflectance(r: np.ndarray) -> Optional[AnalysisWarning]:
    """Given an array of reflectance values (normalized by tyhe reference, not scaled to physical reflectance units),
    this function returns a warning if the mean of the array is greater than 1.5. This suggests that the reference is not
    valid to use with this sample or something unexpected has happened to the sample."""
    assert len(r.shape) == 2
    avg = r.mean()
    if avg > 1.5:
        return AnalysisWarning("R > 1.5", f"Mean reflectance is {avg} (>1.5). Is something wrong with the reference?")
    else:
        return None


def checkMeanSpectraRatio(ratio: float) -> Optional[AnalysisWarning]:
    """For PWS while we expect RMS of the spectra in a region to be similar we don't expect nearby pixels to have well
    correlated spectra. By averaging the spectra of all pixels in a region we can get a `mean spectra`. Ideally we would
    expect this to be flat but realistically we se some variation due to the natural spectral reflectance profile of the sample.
    If this mean spectra changes it suggests something has changed in the system and we want to be aware of this."""
    if ratio > 0.4: #TODO the upper and lower bounds here were arbitrarily chosen without any testing.
        return AnalysisWarning("Mean RMS too high", f"Ratio between variance of mean ROI spectra and mean of spectra variance in ROI is {ratio} (>0.4). This suggests that the ROI is absorbing or fluorescing, or something stranger could be happening.")
    elif ratio < 0.3:
        return AnalysisWarning("Mean RMS too low", f"Ratio between variance of mean ROI spectra and mean of spectra variance in ROI is {ratio} (<0.3). This suggests that the ROI is absorbing or fluorescing, or something stranger could be happening.")
    else:
        return None

def checkRSquared(rSquared: np.ndarray) -> Optional[AnalysisWarning]:
    if np.any(rSquared < 0.7):  # TODO this threshold was arbitrarily chosen.
        return AnalysisWarning("R^2 too low", f"{np.sum(rSquared<0.7)} of the {rSquared.size} elements in our ROI show this problem. The rSquared of our linear fit to the autocorrelation function is (<0.7) the LD and CDR parameters may not not be valid.")
    else:
        return None

