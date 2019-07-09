from pwspy.dataTypes import DynCube
import os
import numpy as np
from pwspy.dataTypes._otherClasses import Roi
#TODO add author and license

wDir = r''
cellNum = list(range(1001, 1015)) # Cell numbers to analyze
mirrorNum = 937 # Flat normalization cube
background = 1997 # Normal cube used for temporal background for noise subtraction

roiName = 'nuc'

ref = DynCube.loadAny(os.path.join(wDir, f'DYN_Cell{mirrorNum}'))

for num in cellNum + [background]: #Loop through all cell folders +1 for background
    dyn = DynCube.loadAny(os.path.join(wDir, f'DYN_Cell{num}'))
    dyn.correctCameraEffects(auto=True)
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
        data = np.fft.irfft(F*np.conjugate(F), axis=1) / F.shape[1] #Autocorrelation #TODO Should check if this matches with other methods of calculating autocorrelation. I read that this might only work if the original data is padded with zeros.
        truncLength = 100
        data = data[:, :truncLength]
        #TODO save it.