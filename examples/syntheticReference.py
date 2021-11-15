# -*- coding: utf-8 -*-
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
