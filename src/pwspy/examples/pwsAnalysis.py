# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 12:38:49 2018

@author: Nick Anthony
"""
from pwspy import ImCube, KCube
import copy
import scipy.signal as sps
import numpy as np

from pwspy.analysis import AnalysisResultsSaver


def analyzeCube(cubeCell: ImCube, darkCount: int, mirror: ImCube, orderFilter: int,
                cutoffFilter: float, wavelengthStart: int, wavelengthStop: int,
                orderPolyFit: int, isAutocorrMinSub: bool, indexAutocorrLinear: int,
                isOpdPolysub: bool, isHannWindow: bool):
    # Indicate the OPD Stop Index.
    indexOpdStop = 100

    cube = copy.deepcopy(cubeCell)  # We don't want to mess up the original cube.

    print("Normalizing ImCubes")
    cube.subtractDarkCounts(darkCount)
    cube.normalizeByExposure()
    mirror.subtractDarkCounts(darkCount)
    mirror.normalizeByExposure()
    cube = cube / mirror

    print("Filtering Signal")
    b, a = sps.butter(orderFilter,
                      cutoffFilter)  # The cutoff totally ignores what the `sample rate` is. so a 2nm interval image cube will be filtered differently than a 1nm interval cube. This is how it is in matlab.
    cube.data = sps.filtfilt(b, a, cube.data, axis=2)

    # The rest of the analysis will be performed only on the selected wavelength range.
    cube = cube.selIndex(wavelengthStart, wavelengthStop)

    # Determine the mean-reflectance for each pixel in the cell.
    reflectance = cube.data.mean(axis=2)

    ## -- Convert to K-Space
    print("Converting to K-Space")
    cube = KCube.fromImCube(cube)

    ## -- Polynomial Fit
    print("Subtracting Polynomial")
    flattenedData = cube.data.reshape((cube.data.shape[0] * cube.data.shape[1], cube.data.shape[2]))
    flattenedData = np.rollaxis(flattenedData, 1)  # Flatten the array to 2d and put the wavenumber axis first.
    cubePoly = np.zeros(flattenedData.shape)  # make an empty array to hold the fit values.
    polydata = np.polyfit(cube.wavenumbers, flattenedData,
                          orderPolyFit)  # At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
    for i in range(orderPolyFit + 1):
        cubePoly += (np.array(cube.wavenumbers)[:, np.newaxis] ** i) * polydata[i,
                                                                       :]  # Populate cubePoly with the fit values.
    cubePoly = np.moveaxis(cubePoly, 0, 1)
    cubePoly = cubePoly.reshape(cube.data.shape)  # reshape back to a cube.

    # Remove the polynomial fit from filtered cubeCell.
    cube.data = cube.data - cubePoly

    ## RMS - POLYFIT
    # The RMS should be calculated on the mean-subtracted polyfit. This may
    # also be accomplished by calculating the standard-deviation.
    rmsPoly = cubePoly.std(axis=2)

    ## -- RMS
    # Obtain the RMS of each signal in the cube.
    rms = cube.data.std(axis=2)

    ## -- Autocorrelation
    print("Calculating Autocorrelation")
    slope, rSquared = cube.getAutoCorrelation(isAutocorrMinSub, indexAutocorrLinear)

    ## OPD Analysis
    print("Calculating OPD")
    if isOpdPolysub:  # If cubeOpdPolysub is to be generated
        opd, xvalOpd = cube.getOpd(isHannWindow, indexOpdStop)
    else:
        opd = xvalOpd = None

    ## Ld Calculation
    k = 2 * np.pi / 0.55
    fact = 1.38 * 1.38 / 2 / k / k
    A1 = 0.008
    A2 = 4
    ld = ((A2 / A1) * fact) * (rms / (-1 * slope.reshape(rms.shape)))
    ## Outputs
    results = AnalysisResultsSaver(
        reflectance=reflectance,
        rms=rms,
        polynomialRms=rmsPoly,
        autoCorrelationSlope=slope,
        rSquared=rSquared,
        ld=ld,
        opd=opd,
        opdIndex=xvalOpd)
    return results


if __name__ == '__main__':
    cube = ImCube.loadAny(r'G:\Calibrations\CellPhantom\lcpws1\5th\Cell1')
    mirror = ImCube.loadAny(r'G:\Calibrations\CellPhantom\lcpws1\5th\Cell666')
    # Default settings
    darkCounts = 1957
    results = analyzeCube(cube, darkCounts, mirror, 6, 0.15, 510, 690, 0, True, 7, True, True)
