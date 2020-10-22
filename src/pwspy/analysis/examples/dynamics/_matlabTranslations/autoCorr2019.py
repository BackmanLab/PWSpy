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

from pwspy.dataTypes import DynCube, Roi
import os
import numpy as np

wDir = r''
cellNum = list(range(1001, 1015)) # Cell numbers to analyze
mirrorNum = 937 # Flat normalization cube, this has been processed by `timeseries2imagecube_general`
background = 1997 # Normal cube used for temporal background for noise subtraction

#It's not clear why there is a mirror and a background. Couldn't you just have one. You could then use the mean of the
# data as the mirror while still extracting noise data.

roiName = 'nuc'

ref = DynCube.loadAny(os.path.join(wDir, f'DYN_Cell{mirrorNum}'))

for num in cellNum + [background]: #Loop through all cell folders +1 for background
    dyn = DynCube.loadAny(os.path.join(wDir, f'DYN_Cell{num}'))
    dyn.correctCameraEffects()
    dyn.normalizeByExposure()
    dyn.normalizeByReference(ref)
    dyn.data = dyn.data - dyn.data.mean(axis=2)[:, :, None] #Subtract the mean of each spectra

    if num == background: #If background then generate a random roi
        # Randomly sample points of background to save space
        sampleSize = 30000
        rows = np.random.choice(dyn.data.shape[0], sampleSize)
        cols = np.random.choice(dyn.data.shape[1], sampleSize)
        mask = np.zeros(dyn.data.shape).astype(np.bool)
        mask[zip(rows, cols)] = True
        rois = [Roi('random', 1, mask, None)]
    else:
        rois = [dyn.loadRoi(roiName, roiNum) for name, roiNum, _ in dyn.getRois() if name == roiName]

    for roi in rois:
        F = np.fft.rfft(dyn.data[roi.mask], axis=1) #FFT of each spectra in the roi
        data = np.fft.irfft(F*np.conjugate(F), axis=1) / F.shape[1] #Autocorrelation
        truncLength = 100
        data = data[:, :truncLength]
        #TODO save the result