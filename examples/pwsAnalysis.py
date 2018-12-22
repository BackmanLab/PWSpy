# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 12:38:49 2018

@author: backman05
"""
from pwspython import ImCube, KCube   
import copy
import scipy.signal as sps
import numpy as np

## analyzeCubeReducedMemory
# Performs analysis on an individual image cube by operating on portions of
# the cube to reduce total memory usage.
def analyzeCube(cubeCell, orderFilter, cutoffFilter, wavelengthStart, wavelengthStop, orderPolyFit, isAutocorrMinSub, indexAutocorrLinear, isOpdFiltered, isOpdPolysub, isHannWindow):
    # Indicate the OPD Stop Index.
    indexOpdStop = 100   

    cube = copy.deepCopy(cubeCell)   #We don't want to mess up the original cube.
    
    cube.normalizeByExposure()    
    mirror.normalizeByExposure()
    cube = cube / mirror
    
    b,a = sps.butter(orderFilter, cutoffFilter) #The cutoff totally ignores what the `sample rate` is. so a 2nm interval image cube will be filtered differently than a 1nm interval cube. This is how it is in matlab.
    cube.data = sps.filtfilt(b,a,cube.data,axis=2)
    
    #The rest of the analysis will be performed only on the selected wavelength range.
    cube = cube.wvIndex(wavelengthStart, wavelengthStop)

    # Determine the mean-reflectance for each pixel in the cell.
    reflectance = cube.data.mean(axis=2)

    ## -- Convert to K-Space
    cube = KCube(cube)

    ## -- Polynomial Fit
    polydata = cube.data.reshape((cube.data.shape[0]*cube.data.shape[1], cube.data.shape[2]))
    polydata = np.rollaxis(polydata,1) #Flatten the array to 2d and put the wavenumber axis first.
    cubePoly = np.zeros(polydata.shape)#make an empty array to hold the fit values.
    polydata = np.polyfit(cube.wavenumbers,polydata,orderPolyFit) #At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
    for i in range(orderPolyFit):
        cubePoly += np.array(cube.wavenumbers)[:,np.newaxis] * polydata[i,:] #Populate cubePoly with the fit values.
    cubePoly = cubePoly.reshape(cube.data.shape) #reshape back to a cube.

    # Remove the polynomial fit from filtered cubeCell.
    cube = cube - cubePoly  

    ## RMS - POLYFIT
    # The RMS should be calculated on the mean-subtracted polyfit. This may
    # also be accomplished by calculating the standard-deviation.
    rmsPoly = cubePoly.data.std(axis=2)

    ## -- RMS
    # Obtain the RMS of each signal in the cube.
    rms = cube.data.std(axis=2)

    ## -- Autocorrelation
    slope, rSquared = cube.getAutoCorrelation(isAutocorrMinSub, indexAutocorrLinear)

    ## OPD Analysis
    if isOpdPolysub:   # If cubeOpdPolysub is to be generated
        opd, xvalOpd = cube.getOpd(isHannWindow, indexOpdStop)  

    ## Ld Calculation
    k = 2 * np.pi / 0.55
    fact = 1.38 * 1.38 / 2 / k / k;
    A1 = 0.008
    A2 = 4
    ld = ((A2 / A1) * fact) * (cubeRms / (-1 * cubeSlope))
    ## Outputs
    results = {
            'reflectance': reflectance,
            'rms': rms,
            'polynomialRms': rmsPoly,
            'autoCorrelationSlope': slope,
            'rSquared': rSquared,
            'ld': ld,
            'opd': opd,
            'xvalOpd': xvalOpd}
    return results
