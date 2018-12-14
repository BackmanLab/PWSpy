# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 12:38:49 2018

@author: backman05
"""
from pwspython import ImCube, KCube   
import copy

## analyzeCubeReducedMemory
# Performs analysis on an individual image cube by operating on portions of
# the cube to reduce total memory usage.
def analyzeCube(cubeCell, orderFilter, cutoffFilter, wavelengthStart, wavelengthStop, orderPolyfit, isAutocorrMinSub, indexAutocorrLinear, isOpdFiltered, isOpdPolysub, isHannWindow):
    # Indicate the OPD Stop Index.
    indexOpdStop = 100   

    cube = copy.deepCopy(cubeCell)   #We don't want to mess up the original cube.
    
    cube.normalizeByExposure()    
    mirror.normalizeByExposure()
    cube = cube / mirror
    
    cube = pws.analysis.filterCube(cube, orderFilter, cutoffFilter);
    
    #The rest of the analysis will be performed only on the selected wavelength range.
    cube = cube.wvIndex(wavelengthStart, wavelengthStop)

    # Determine the mean-reflectance for each pixel in the cell.
    reflectance = cube.data.mean(axis=2)

    ## -- Convert to K-Space
    cube = KCube(cube)

    ## -- Polynomial Fit
    cubePoly = pws.analysis.polynomialFit(cube, wavenumberList, orderPolyfit);

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
    if isOpdPolysub    # If cubeOpdPolysub is to be generated
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
