# -*- coding: utf-8 -*-
"""
Created on Tue Jan  8 10:07:20 2019

@author: backman05
"""

from pwspython import ImCube, KCube
import matplotlib.pyplot as plt
import scipy.signal as sps
import os
import numpy as np
import sys

path = r'G:\Calibrations\CellPhantom\lcpws1\5th'
refName = 'Cell666'     #This is an imcube of glass, used for normalization.
resinName = 'Cell1'     #An ROI will be selected from this imcube to generate the OPD for the resin.
cellNames = ['Cell1', 'Cell2', 'Cell3', 'Cell4']
    
# identify the depth in um to which the OPD spectra need to be integrated
opdIntegralEnd = 2.0 ##  in um
isHannWindow = True #Should Hann windowing be applied to eliminate edge artifacts?
subtractResinOpd = False

resin_OPD_subtraction = True
wvStart = 510     #start wavelength for poly subtraction
wvEnd = 690     # end wavelength for poly subtraction
orderPolyFit = 0
wv_step = 2
RIsample = 1.545
SavePixelwiseRMS_OPDint = True
darkCount = 101
wv_step = 2

b,a = sps.butter(6, 0.1*wv_step) #The cutoff totally ignores what the `sample rate` is. so a 2nm interval image cube will be filtered differently than a 1nm interval cube. This is how it is in matlab.

 ### load and save mirror or glass image cube
ref = ImCube.loadAny(os.path.join(path,refName))
ref.subtractDarkCounts(darkCount)
ref.normalizeByExposure()
    
if subtractResinOpd:
    ### load and save reference empty resin image cube
    resin = ImCube.loadAny(os.path.join(path,resinName))
    resin.subtractDarkCounts(darkCount)
    resin.normalizeByExposure()
    resin /= ref
    resin = KCube(resin)
    mask = resin.selectLassoROI()
    OPD_resin, xvals = resin.getOpd(isHannWindow, 100, mask)

for cellName in cellNames:               
    cube = ImCube.loadAny(os.path.join(path,cellName))
    cube.subtractDarkCounts(darkCount)
    cube.normalizeByExposure()
    cube /= ref
    cube.data = sps.filtfilt(b,a,cube.data,axis=2)
    cube = KCube(cube)

    ## -- Polynomial Fit
    print("Subtracting Polynomial")
    polydata = cube.data.reshape((cube.data.shape[0]*cube.data.shape[1], cube.data.shape[2]))
    polydata = np.rollaxis(polydata,1) #Flatten the array to 2d and put the wavenumber axis first.
    cubePoly = np.zeros(polydata.shape)#make an empty array to hold the fit values.
    polydata = np.polyfit(cube.wavenumbers,polydata,orderPolyFit) #At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
    for i in range(orderPolyFit + 1):
        cubePoly += (np.array(cube.wavenumbers)[:,np.newaxis]**i) * polydata[i,:] #Populate cubePoly with the fit values.
    cubePoly = np.moveaxis(cubePoly, 0, 1)
    cubePoly = cubePoly.reshape(cube.data.shape) #reshape back to a cube.
    # Remove the polynomial fit from filtered cubeCell.
    cube.data = cube.data - cubePoly                                  

    # Find the fft for each signal in the desired wavelength range
    opdData, xvals = cube.getOpd(isHannWindow, 100)
    
    if subtractResinOpd:
        opdData = opdData - abs(OPD_resin) #why is this abs?

    rmsData = np.sqrt(np.mean(cube.data**2, axis=2)) 
    integralStopIdx = np.where(xvals>=opdIntegralEnd)[0][0]
    rmsOpdIntData = np.sqrt(np.abs(1/(2*np.pi)*np.sum(opdData[:,:,:integralStopIdx]**2,axis=2)))/2

    
    if SavePixelwiseRMS_OPDint:
        cmap = plt.get_cmap('jet')
        fig, axs = plt.subplots(1,2)
        im = axs[0].imshow(rmsData, cmap=cmap)
        fig.colorbar(im, ax=axs[0])
        axs[0].set_title('RMS')
        im = axs[1].imshow(rmsOpdIntData, cmap=cmap)
        fig.colorbar(im, ax=axs[1])
        axs[1].set_title(f'RMS from OPD below {opdIntegralEnd} after resin OPD subtraction')              


