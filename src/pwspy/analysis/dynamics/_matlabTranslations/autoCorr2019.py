from pwspy.dataTypes.data import DynCube
import os
import numpy as np
from pwspy.dataTypes._otherClasses import Roi

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
    dyn.data = dyn.data - dyn.data.mean(axis=2)[:, :, None] #Subtract the mean of each spectra #TODO what is the purpose of this?

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
        data = np.fft.irfft(F*np.conjugate(F), axis=1) / F.shape[1] #Autocorrelation #TODO Should check if this matches with other methods of calculating autocorrelation. I read that this might only work if the original data is padded with zeros.
        truncLength = 100
        data = data[:, :truncLength]
        #TODO save it.