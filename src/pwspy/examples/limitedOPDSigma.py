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
This script is based on a matlab script written by Lusik Cherkezyan for Nanocytomics.
Nano uses this method to extract rms from phantom make from ChromEM cells embedded in resin.
The phantom has a strong thin-film spectrum. This script is meant to filter out the thin film components
of the fourier transfrom and extract RMS from what is left.
"""

# Last tested on pwspy ad745ef0c1ae526e25981b0036f460981397a456


from pwspy.dataTypes import CameraCorrection, AcqDir, Roi, ImCube, KCube
import matplotlib.pyplot as plt
import scipy.signal as sps
import os
import sys
import numpy as np
import scipy as sp

if __name__ == '__main__':

    '''User Input'''
    path = r'2_7_2019 11.07'
    refName = 'Cell999'  # This is an imcube of glass, used for normalization.
    cellNames = ['Cell1', 'Cell2']  # , 'Cell3', 'Cell4','Cell5']
    maskSuffix = 'resin'

    # identify the depth in um to which the OPD spectra need to be integrated
    integrationDepth = 2.0  ##  in um
    isHannWindow = True  # Should Hann windowing be applied to eliminate edge artifacts?
    subtractResinOpd = True
    resetResinMasks = False
    wvStart = 510  # start wavelength for poly subtraction
    wvEnd = 690  # end wavelength for poly subtraction
    sampleRI = 1.545  # The refractive index of the resin. This is taken from matlab code, I don't know if it's correct.
    orderPolyFit = 0
    wv_step = 2
    correction = CameraCorrection(2000, (0.977241216, 1.73E-06, 1.70E-11))

    '''************'''

    b, a = sps.butter(6, 0.1 * wv_step)
    opdIntegralEnd = integrationDepth * 2 * sampleRI  # We need to convert from our desired depth into an opd value. There are some questions about having a 2 here but that's how it is in the matlab code so I'm keeping it.

    ### load and save mirror or glass image cube
    ref = ImCube.fromMetadata(AcqDir(os.path.join(path, refName)).pws)
    ref.correctCameraEffects(correction)
    ref.filterDust(6, pixelSize=1)
    ref.normalizeByExposure()

    if subtractResinOpd:
        ### load and save reference empty resin image cube
        fig, ax = plt.subplots()
        resinOpds = {}
        for cellName in cellNames:
            resin = ImCube.fromMetadata(AcqDir(os.path.join(path, cellName)).pws)
            resin.correctCameraEffects(correction)
            resin.normalizeByExposure()
            resin /= ref
            resin = KCube.fromImCube(resin)
            if resetResinMasks:
                [resin.metadata.acquisitionDirectory.deleteRoi(name, num) for name, num, fformat in resin.metadata.acquisitionDirectory.getRois() if name == maskSuffix]
            if maskSuffix in [name for name, number, fformat in resin.metadata.acquisitionDirectory.getRois()]:
                resinRoi = resin.metadata.acquisitionDirectory.loadRoi(maskSuffix, 1)
            else:
                print('Select a region containing only resin.')
                resinRoi = Roi.fromVerts(maskSuffix, 1, resin.selectLassoROI(), resin.data.shape[:2])
                resin.metadata.acquisitionDirectory.saveRoi(resinRoi)
            resin.data -= resin.data.mean(axis=2)[:, :, np.newaxis]
            opdResin, xvals = resin.getOpd(isHannWindow, indexOpdStop=None, mask=resinRoi.mask)
            resinOpds[cellName] = opdResin
            ax.plot(xvals, opdResin, label=cellName)
            ax.vlines([opdIntegralEnd], ymin=opdResin.min(), ymax=opdResin.max())
            ax.set_xlabel('OPD')
            ax.set_ylabel("Amplitude")
        ax.legend()
        plt.pause(0.2)

    rmses = {}  # Store the rms maps for later saving
    for cellName in cellNames:
        cube = ImCube.fromMetadata(AcqDir(os.path.join(path, cellName)).pws)
        cube.correctCameraEffects(correction)
        cube.normalizeByExposure()
        cube /= ref
        cube.data = sps.filtfilt(b, a, cube.data, axis=2)
        cube = KCube.fromImCube(cube)

        ## -- Polynomial Fit
        print("Subtracting Polynomial")
        polydata = cube.data.reshape((cube.data.shape[0] * cube.data.shape[1], cube.data.shape[2]))
        polydata = np.rollaxis(polydata, 1)  # Flatten the array to 2d and put the wavenumber axis first.
        cubePoly = np.zeros(polydata.shape)  # make an empty array to hold the fit values.
        polydata = np.polyfit(cube.wavenumbers, polydata,
                              orderPolyFit)  # At this point polydata goes from holding the cube data to holding the polynomial values for each pixel. still 2d.
        for i in range(orderPolyFit + 1):
            cubePoly += (np.array(cube.wavenumbers)[:, np.newaxis] ** i) * polydata[i,
                                                                           :]  # Populate cubePoly with the fit values.
        cubePoly = np.moveaxis(cubePoly, 0, 1)
        cubePoly = cubePoly.reshape(cube.data.shape)  # reshape back to a cube.
        # Remove the polynomial fit from filtered cubeCell.
        cube.data = cube.data - cubePoly

        rmsData = np.sqrt(np.mean(cube.data ** 2, axis=2)) #This can be compared to rmsOPDIntData, when the integralStopIdx is high and we don't do spectral subtraction they should be equivalent.

        # Find the fft for each signal in the desired wavelength range
        opdData, xvals = cube.getOpd(isHannWindow, None)

        if subtractResinOpd:
            opdData = opdData - resinOpds[cellName]

        try:
            integralStopIdx = np.where(xvals >= opdIntegralEnd)[0][0]
        except IndexError:  # If we get an index error here then our opdIntegralEnd is probably bigger than we can achieve. Just use the biggest value we have.
            integralStopIdx = None
            opdIntegralEnd = max(xvals)
            print(f'Integrating to OPD {opdIntegralEnd}')

        opdSquared = np.sum(opdData[:, :, :integralStopIdx] ** 2,axis=2)  # Parseval's theorem tells us that this is equivalent to the sum of the squares of our original signal
        opdSquared *= len(cube.wavenumbers) / opdData.shape[2]  # If the original data and opd were of the same length then the above line would be correct. Since the fft has been upsampled. we need to normalize.
        rmsOpdIntData = np.sqrt(opdSquared)  # this should be equivalent to normal RMS if our stop index is high and resin subtraction is disabled.

        cmap = plt.get_cmap('jet')
        fig, axs = plt.subplots(1, 2, sharex=True, sharey=True)
        im = axs[0].imshow(rmsData, cmap=cmap, clim=[np.percentile(rmsData, 0.5), np.percentile(rmsData, 99.5)])
        fig.colorbar(im, ax=axs[0])
        axs[0].set_title('RMS')
        im = axs[1].imshow(rmsOpdIntData, cmap=cmap,
                           clim=[np.percentile(rmsOpdIntData, 0.5), np.percentile(rmsOpdIntData, 99.5)])
        fig.colorbar(im, ax=axs[1])
        axs[1].set_title(f'RMS from OPD below {opdIntegralEnd} after resin OPD subtraction')
        fig.suptitle(cellName)
        rmses[cellName] = rmsOpdIntData
        plt.pause(0.2)
    plt.pause(0.5)

    ## plt.waitforbuttonpress(timeout=-1)
    #for k, v in rmses.items():
    #    if input(f"Save opdRms for {k}? (y/n): ").strip().lower() == 'y':
    #        sp.io.savemat(os.path.join(path, k, 'phantom_Rms.mat'), {'cubeRms': v.astype(np.float32)})  # save as a single
