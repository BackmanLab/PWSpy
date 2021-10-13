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
from pwspy.examples import PWSImagePath

if __name__ == '__main__':
    plt.ion()
    a = pwsdt.Acquisition(PWSImagePath).pws.toDataClass()

    roi = a.selectLassoROI()
    spec, std = a.getMeanSpectra(mask=roi)
    newData = np.zeros(a.data.shape)
    newData[:, :, :] = spec[np.newaxis, np.newaxis, :]
    ref = pwsdt.PwsCube(newData, a.metadata)

    plt.plot(a.wavelengths, spec)

    a = 1
