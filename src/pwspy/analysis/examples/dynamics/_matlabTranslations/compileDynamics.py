from pwspy.dataTypes import Roi
from pwspy.dataTypes._data import DynCube
import numpy as np
import os
import pandas as pd

#TODO this is very nonfunctional. just a sketch

wDir = r''
cellNums = range(1001, 1015)
background = 1997  # Temporal Background for noise subtraction
bwName = 'nuc'
n_medium = 1.37  # RI of the media (avg RI of chromatin)

sigmaCells = range(1, 15)
sigmaName = 'p0'

fileName = f'{bwName}_Autocorr'
dataAutocorr = {}
dataDiff = []

output = []

bgCube = DynCube.loadAny(os.path.join(wDir, f'Cell{background}'))
backgroundACF = bgCube.getAutocorr() #The background ACF

for cellNum in cellNums:
    cube = DynCube.loadAny(os.path.join(wDir, f'Cell{cellNum}'))
    rois = cube.metadata.getRois()
    for roi in rois:
        an = cube.loadAnalysis()
        ac = cube.getAutocorrelation()
        bLim = backgroundACF[:,:,0][roi.mask].mean() #The mean background ACF0 value for the ROI
        rmsT_sq = (ac[:,:,0] - bLim).mean()  # background subtracted sigma_t^2

        # Remove pixels with low SNR. default threshold removes values where first ACF point is less than sqrt(2) of background ACF
        ac = ac[ac[:, :, 0] > np.sqrt(2)*bLim[:,:,None]]

        normBsCorr = ac - backgroundACF[roi.mask[:,:,None]]  # Background Subtraction
        normBsCorr = normBsCorr / np.abs(normBsCorr[:, 0])[:, None]  # Normalization

        # Remove negative values before taking log
        normBsCorr[normBsCorr < 0] = np.nan

        dt = cube.times[1] - cube.times[0]
        k = (n_medium * 2 * np.pi) / cube.metadata.wavelength
        dSlope = np.diff(np.log(normBsCorr).mean(axis=(0, 1))) / (dt*4*k**2)
        dSlope = dSlope[0]

        output.append({'Cell #': f'{cellNum}_{roi.name}{roi.number}',
         'D': dSlope,
         'Sigma_t^2 (b sub)': rmsT_sq,
         'Sigma_s': an.rms[roi.mask].mean(),
         'Reflectance': an.reflectance[roi.mask].mean()})

output = pd.DataFrame(output)



