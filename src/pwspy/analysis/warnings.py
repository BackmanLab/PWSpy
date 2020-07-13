# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

"""
The purpose of this file is provide functions which check data during analysis for abnormality. If abnormal conditions are found
then an AnalysisWarning is produced. The application can then display or record these warnings. This aspect of the program has not really
been fully implemented.
"""

from typing import Optional
import numpy as np
#TODO actually use these!


class AnalysisWarning:
    """Each warning should have a short description and a longer explanation.

    Args:
        shortMsg: A brief explanation of the warning.
        longMsg: A longer in depth explanation.
    """
    def __init__(self, shortMsg: str, longMsg: str):
        self.longMsg = longMsg
        self.shortMsg = shortMsg


def checkMeanSpectraRatio(ratio: float) -> Optional[AnalysisWarning]:
    """For PWS while we expect RMS of the spectra in a region to be similar we don't expect nearby pixels to have well
    correlated spectra. By averaging the spectra of all pixels in a region we can get a `mean spectra`. Ideally we would
    expect this to be flat but realistically we se some variation due to the natural spectral reflectance profile of the sample.
    If this mean spectra changes it suggests something has changed in the system and we want to be aware of this."""
    if ratio > 0.4: #TODO the upper and lower bounds here were arbitrarily chosen without any testing.
        return AnalysisWarning("Mean RMS ratio too high", f"Ratio between variance of mean ROI spectra and mean of spectra variance in ROI is {ratio} (>0.4). This suggests that the ROI is absorbing or fluorescing, or something stranger could be happening.")
    elif ratio < 0.3:
        return AnalysisWarning("Mean RMS ratio too low", f"Ratio between variance of mean ROI spectra and mean of spectra variance in ROI is {ratio} (<0.3). This suggests that the ROI is absorbing or fluorescing, or something stranger could be happening.")
    else:
        return None


def checkRSquared(rSquared: np.ndarray) -> Optional[AnalysisWarning]:
    """We try to fit a line to the natural log of the autocorrelation function in order to find the slope. The RSquared
    tells us how well this fit worked. If RSquared is too low then we can't really trust the slop value that we calculated."""
    if np.any(rSquared < 0.7):  # TODO this threshold was arbitrarily chosen.
        return AnalysisWarning("R^2 too low", f"{np.sum(rSquared<0.7)} of the {rSquared.size} elements in our ROI show this problem. The rSquared of our linear fit to the autocorrelation function is (<0.7) the LD and CDR parameters may not not be valid.")
    else:
        return None

