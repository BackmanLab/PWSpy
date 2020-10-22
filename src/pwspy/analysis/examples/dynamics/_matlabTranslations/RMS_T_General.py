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

from pwspy.dataTypes import DynCube
import os
from glob import glob

wDir = r''
refPath = r''

ref = DynCube.loadAny(refPath)
ref.correctCameraEffects()
ref.normalizeByExposure()

files = glob(os.path.join(wDir, 'Cell*'))
for f in files:
    dyn = DynCube.loadAny(f)
    dyn.correctCameraEffects()
    dyn.normalizeByExposure()
    dyn.normalizeByReference(ref)

    # The original MATLAB script optionally uses 3 frame frame-averaging here as a lowpass, That hasn't been implemented here

    #This is equivalent to subtracting the mean from each spectra and taking the RMS
    rms = dyn.data.std(axis=2)

    #TODO save the RMS