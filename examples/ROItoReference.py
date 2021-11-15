
# -*- coding: utf-8 -*-
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

