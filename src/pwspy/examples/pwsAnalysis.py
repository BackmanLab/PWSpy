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

# -*- coding: utf-8 -*-
"""
An adaptation of the PWS analysis script used in MATLAB. This is now outdated. The up to date version is in
`pwspy.analysis.pws`.
"""
import logging

from pwspy.dataTypes import ImCube, KCube
import copy
import scipy.signal as sps
import numpy as np

from pwspy.analysis.pws import PWSAnalysisResults


def analyzeCube(cubeCell: ImCube, darkCount: int, mirror: ImCube, orderFilter: int,
                cutoffFilter: float, wavelengthStart: int, wavelengthStop: int,
                orderPolyFit: int, isAutocorrMinSub: bool, indexAutocorrLinear: int,
                isOpdPolysub: bool, isHannWindow: bool):
    # Indicate the OPD Stop Index.
    indexOpdStop = 100

    logger = logging.getLogger(__name__)

    cube = copy.deepcopy(cubeCell)  # We don't want to mess up the original cube.

    logger.info("Normalizing ImCubes")
    cube.subtractDarkCounts(darkCount)
    cube.normalizeByExposure()
    mirror.subtractDarkCounts(darkCount)
    mirror.normalizeByExposure()
    cube = cube / mirror

    logger.info("Filtering Signal")
    b, a = sps.butter(orderFilter,
                      cutoffFilter)  # The cutoff totally ignores what the `sample rate` is. so a 2nm interval image cube will be filtered differently than a 1nm interval cube. This is how it is in matlab.
    cube.data = sps.filtfilt(b, a, cube.data, axis=2)

    # The rest of the analysis will be performed only on the selected wavelength range.
    cube = cube.selIndex(wavelengthStart, wavelengthStop)

    # Determine the mean-reflectance for each pixel in the cell.
    reflectance = cube.data.mean(axis=2)

    ## -- Convert to K-Space
    logger.info("Converting to K-Space")
    cube = KCube.fromImCube(cube)

    ## -- Polynomial Fit
    logger.info("Subtracting Polynomial")
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
    logger.info("Calculating Autocorrelation")
    slope, rSquared = cube.getAutoCorrelation(isAutocorrMinSub, indexAutocorrLinear)

    ## OPD Analysis
    logger.info("Calculating OPD")
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
    results = PWSAnalysisResults.create(
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
