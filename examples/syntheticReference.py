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
This script blurs an image cube in the xy direction. Allows you to turn an
image of cells into something that can be used as a reference image, assuming
most of the the FOV is glass. In reality you should just have a good reference image to use and not resort to something
like this.
"""

import copy

import matplotlib.pyplot as plt
import pwspy.dataTypes as pwsdt
from examples import PWSImagePath

plt.ion()

acq = pwsdt.Acquisition(PWSImagePath)
a = acq.pws.toDataClass()

a.correctCameraEffects()  # Correct for dark counts and potentially for camera nonlinearity using metadata stored with the original measurement.
a.normalizeByExposure()  # Divide by exposure time to get data in units of `counts/ms`. This isn't strictly necessary in this case.

mirror = copy.deepcopy(a)
mirror.filterDust(10)  # Apply a gaussian blurring with sigma=10 microns along the XY plane.

a.plotMean()  # Plot the mean reflectance of the original
mirror.plotMean()  # Plot the mean reflectance after filtering.
a.normalizeByReference(mirror)  # Normalize raw by reference
a.plotMean()  # Plot the measurement after normalization.
plt.figure()
plt.imshow(a.data.std(axis=2))  # Plot RMS after normalization.
