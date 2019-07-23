from pwspy.dataTypes import DynCube, Roi
import numpy as np
import os

#TODO this is very nonfunctional. just a sketch

wDir = r''
cellNums = range(1001, 1015)
mirrornum = 937 # Flat Normalization cube
background = 1997  # Temporal Background for noise subtraction
bwName = 'nuc'
n_medium = 1.37 #RI of the media (avg RI of chromatin)


k = (n_medium * 2 * np.pi) / wavelength

sigmaCells = range(1,15)
sigmaName = 'p0'

fileName = f'{bwName}_Autocorr'
dataAutocorr = {}
dataDiff = []

dataTempD=['Cell #', 'D', 'Sigma_t^2 (b sub)', 'Sigma_s', 'Reflectance']

roi = DynCube.loadRoi(bwName, 1)
bgCube = DynCube.loadAny(os.path.join(wDir, f'Cell{background}'))
ac = bgCube.getAutocorr() #'BW1_fullFOV_Autocorr.mat', get xVals too
meanBackground = ac.getMeanSpectra(roi)
bLim = meanBackground[0]

for cellNum in cellNums:
    cube = DynCube.loadAny(os.path.join(wDir, f'Cell{cellNum}'))
    rois = cube.metadata.getRois()
    for roi in rois:
        an = cube.loadAnalysis()
        ac = cube.getAutocorrelation()
        rmsT_sq = (ac - bLim).mean() #  background subtracted sigma_t^2

        #Remove pixels with low SNR. default threshold removes values where first ACF point is less than sqrt(2) of background ACF
        ac = ac[ac[:, 0] > np.sqrt(2)*bLim, :]

        normBsCorr = ac - meanBackground #  Background Subtraction

        normBsCorr = normBsCorr / np.abs(normBsCorr[:, 0])[:, None] #  Normalization

        #Remove negative values before taking log
        normBsCorr[normBsCorr < 0] = np.nan

        dt = xVals[1] - xVals[0]
        dSlope = np.diff(np.log(normBsCorr).mean(axis=?)) / (dt*4*k**2)
        dSlope = dSlope[0]

        dataTempD = cat(2, dataTempD, [{['Cell', num2str(cellNum(i)), '_', char(ACFList(d))]},
                                       num2cell(d_slope),
                                       num2cell(rmsT_sq),
                                       mean(cubeRms(BW)),
                                       mean(cubeReflectance(BW))])

    dataDiff(size(dataDiff, 1) + 1, 1) = patList(f)
    dataDiff(size(dataDiff, 1) + 1:size(dataDiff, 1) + size(dataTempD, 1), 1 : size(dataTempD, 2)) = dataTempD



