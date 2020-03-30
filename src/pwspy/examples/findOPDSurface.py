from pwspy.dataTypes import KCube, AcqDir
from pwspy.analysis.pws import PWSAnalysisResults
from glob import glob
import os
import scipy as sp
import numpy as np

rootDir = r''
anName = 'p0'
sigma = 1 # Blur radius in microns
opdCutoff = 3

files = glob(os.path.join(rootDir, 'Cell*'))
acqs = [AcqDir(f) for f in files]
for acq in acqs:
    an = acq.pws.loadAnalysis(anName)
    refl = an.reflectance
    opd, opdIndex = refl.getOpd(isHannWindow=True)  # Using the Hann window should improve dynamic range and reduce false peaks from frequency leakage.

    # Remove the low OPD signal.
    idx = np.argmin(np.abs(opdIndex - opdCutoff))
    opd = opd[:, :, idx:]
    opdIndex = opdIndex[idx:]

    # Blur laterally
    sigma = sigma / acq.pws.pixelSizeUm  # convert from microns to pixels
    for i in range(opd.shape[2]):
        opd[:, :, i] = sp.ndimage.filters.gaussian_filter(opd[:, :, i], sigma, mode='reflect')

    arr = np.zeros_like(opd[:,:,0], dtype=object)
    for i in range(opd.shape[0]):
        for j in range(opd.shape[1]):
            arr[i, j] = sp.signal.find_peaks(opd[i, j, :])  # TODO vectorize? use kwargs?

    a = 1#debug here