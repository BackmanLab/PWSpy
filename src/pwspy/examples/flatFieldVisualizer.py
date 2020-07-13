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
A script that attempts to reveal information about the spectral uniformity accross the field of view of the microscope.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pwspy.dataTypes import ExtraReflectanceCube, ExtraReflectionCube, ImCube
from pwspy.utility.reflection import reflectanceHelper, Material
from glob import glob
import os
from pwspy.utility import thinFilmPath
from pwspy.dataTypes import Roi

#TODO change the theoretical CSV file to use BK7 instead of SIO2. Our measurements are still not matching theory though. Is this because of all the extra scattering?

plt.ion()
__spec__ = None


def colorbar(mappable):
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    ax = mappable.axes
    fig = ax.figure
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    return fig.colorbar(mappable, cax=cax)

if __name__ == "__main__":
    # %%User Input
    wDir = r'J:\Calibrations\ITOThinFilm\LCPWS2'
    referenceMaterial = Material.Water
    referenceNumber = 999
    cellNumber = 1
    
    files = glob(os.path.join(wDir, '*'))
    files = [f for f in files if os.path.isdir(f)]
    
    
    # %% Loading
    theory = pd.read_csv(os.path.join(thinFilmPath, '2um_sio2_ITO_air.txt'), delimiter='\t', index_col=0)
    theory = theory.loc[500:700:2]
    theory = theory
    ztheory = (theory - theory.mean()) / (theory.std() * theory.shape[0])  # Zero normalize for correlation
    sref = reflectanceHelper.getReflectance(referenceMaterial, Material.Glass, index=range(500, 701, 2))

    result = []
    for f in files:
        print("Loading")
        im = ImCube.loadAny(os.path.join(f, f'Cell{cellNumber}'))
        ref = ImCube.loadAny(os.path.join(f, f'Cell{referenceNumber}'))
        er = ExtraReflectanceCube.fromHdfFile(r'C:\Users\backman05\PwspyApps\ExtraReflectanceCreatorData\GoogleDriveData', 'LCPWS2_100xpfs-7_8_2019')
        print("Dividing data by mirror spectra")
        im.correctCameraEffects()
        ref.correctCameraEffects()
        im.normalizeByExposure()
        ref.normalizeByExposure()
        Iextra = ExtraReflectionCube.create(er, sref, ref)
        im.subtractExtraReflection(Iextra)
        ref.subtractExtraReflection(Iextra)
        mSpectra = ref.getMeanSpectra()[0] # we just want an average spectra to normalize by so we don't normalize out effects that we want to see.
        im /= mSpectra[None, None, :]
        im *= np.array(sref) # Normalize to physical reflectance
        zim = (im.data - im.data.mean(axis=2, keepdims=True)) / (im.data.std(axis=2, keepdims=True))  # zero normalize for correlation
        print("Cross correlating with theory")
        corr = np.apply_along_axis(lambda arr: np.correlate(np.array(ztheory).squeeze(), arr, mode='same'), axis=2, arr=zim)

        # Data Extraction
        print("Extracting data from correlation")
        amp = im.data.max(axis=2) - im.data.min(axis=2)  # The amplitude of the spectra.
        corramp = np.max(corr, axis=2)  # The strength of the correlation
        corrmax = np.argmax(corr, axis=2) - corr.shape[2] // 2  # The shift in index that gives the strongest correlation.
        minn = (im.data.min(axis=2) - np.array(
            theory).min())  # The difference between the minimum of the spectra and the theoretical minima. this indicates unwanted light.
        result.append((im, amp, corramp, corrmax, minn))


    for im, amp, corramp, corrmax, minn in result:
        # Plotting
        fig, axs = plt.subplots(nrows=2, ncols=2)
        fig.suptitle(os.path.split(im.metadata.filePath)[-1])
        imsh = axs[0, 0].imshow(amp, vmin=np.percentile(amp, 1), vmax=np.percentile(amp, 99))
        colorbar(imsh)
        axs[0, 0].set_title("Amplitude")
        imsh = axs[0, 1].imshow(corrmax, vmin=np.percentile(corrmax, 1), vmax=np.percentile(corrmax, 99))
        colorbar(imsh)
        axs[0, 1].set_title("Shift (index) to max correlation")
        imsh = axs[1, 1].imshow(corramp, vmin=0, vmax=1)
        colorbar(imsh)
        axs[1, 1].set_title("Max Correlation")
        imsh = axs[1, 0].imshow(minn, vmin=np.percentile(minn, 1), vmax=np.percentile(minn, 99))
        colorbar(imsh)
        axs[1, 0].set_title("Minimum of data")
        for ax in axs.flatten():
            ax.axis('off')

    while True:
        try:
            mask = Roi.fromVerts('null', 1, result[0][0].selectLassoROI(), dataShape=result[0][0].data.shape[:-1])
            fig2, ax = plt.subplots()
            ax.plot(np.array(theory.index).astype(np.float), np.array(theory["Reflectance"]).astype(np.float),
                    label="Theory")
            for im, amp, corramp, corrmax, minn in result:
                mean, std = im.getMeanSpectra(mask)
                ax.plot(im.wavelengths, mean, label=os.path.split(im.metadata.filePath)[-1])
                ax.fill_between(im.wavelengths, mean - std, mean + std, alpha=0.4)
            ax.legend()
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Reflectance")
            fig2.suptitle("Thin Film Comparison")
            fig2.show()
            plt.pause(0.1)
            while plt.fignum_exists(fig2.number):
                fig2.canvas.flush_events()
        except Exception as e:
            raise e
    
