
# -*- coding: utf-8 -*-
# Copyright 2018-2021 Nick Anthony, Backman Biophotonics Lab, Northwestern University
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
This script allows the user to select a region of an PwsCube. the spectra of this
region is then averaged over the X and Y dimensions. This spectra is then saved
as a reference dataTypes with the same initial dimensions.
Can help to make a reference when you don't actually have one for some reason
"""

import pwspy.dataTypes as pwsdt
import matplotlib.pyplot as plt
import numpy as np
from examples import PWSImagePath

plt.ion()
a = pwsdt.Acquisition(PWSImagePath).pws.toDataClass()  # Load a measurement from file.

roi = a.selectLassoROI()  # Prompt the user for a hand-drawn ROI
spec, std = a.getMeanSpectra(mask=roi)  # Get the average spectra within the ROI
newData = np.zeros(a.data.shape)
newData[:, :, :] = spec[np.newaxis, np.newaxis, :]  # Extend the averaged spectrum along the full dimensions of the original measurement.
ref = pwsdt.PwsCube(newData, a.metadata)  # Create a new synthetic measurement using the averaged spectrum
plt.plot(a.wavelengths, spec)

