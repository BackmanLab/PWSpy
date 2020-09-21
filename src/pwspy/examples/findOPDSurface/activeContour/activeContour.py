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



import pickle
import numpy as np
from skimage import morphology
import matplotlib.pyplot as plt
from skimage import filters
import multiprocessing as mp
import pwspy.dataTypes as pwsdt
from pwspy.examples.findOPDSurface.activeContour.funcs import volume3Dto2D, termSeg, morphSmoothing3D, equalAxis3dPlot
import scipy as sp
from glob import glob
import os
from matplotlib import cm


def seg(cellDir: str):
    """This function is run on multiple cores at once so that the full procedure finishes faster.

    Args:
        cellDir: The file path to a PWS acquisition.

    Returns:
        A tuple containing:
            snake: The result of the segmentation. 3d boolean array.
            snake2: The result of the segmentation with morphological smoothing applied. 3d booleaan array.
            opdIndex: The 1d array giving the OPD value at each slice along the 3rd axis of `snake`.

    """
    try:
        anName = 'p0'  # The name of the analysis to load.
        opdCutoffLow = 0  # In preprocessing data below this OPD value will be excluded
        opdCutoffHigh = 25  # In preprocessing data above this OPD value will be excluded

        acq = pwsdt.AcqDir(cellDir) # Load a handle to the acquisition
        an = acq.pws.loadAnalysis(anName)  # Load the analysis results object
        opd, opdIndex = an.reflectance.getOpd(isHannWindow=True)  # Using the Hann window should improve dynamic range and reduce false peaks from frequency leakage.

        # Remove the low and high OPD signal.
        idxLow = np.argmin(np.abs(opdIndex - opdCutoffLow))
        idxHigh = np.argmin(np.abs(opdIndex - opdCutoffHigh))
        opd = opd[:, :, idxLow:idxHigh]
        opdIndex = opdIndex[idxLow:idxHigh]

        # Use RMS ot generate a mask showing where the cells are.
        signal = an.rms  # RMS. Use it to detect background
        thresh = filters.threshold_li(signal)  # Threshold between high-signal and low-signal regions.
        mask = signal < thresh  # Mask that should indicate all regions outside a cell.
        disk = morphology.disk(3)
        mask = morphology.binary_opening(mask, disk)  # Get rid of small isolated regions in the mask.

        #Use the mask from the previous step to generate an rough initial guess for the segmentation. This will be our starting point to save us some iterations.
        level_set = (~mask[:, :, None]) * np.ones(opd.shape)
        level_set[:, :, opd.shape[2] // 2:] = False

        # Blur laterally to denoise. This step is vital (I think)
        sigma = 0.5
        Sigma = sigma / acq.pws.pixelSizeUm  # convert from microns to pixels
        for i in range(opd.shape[2]):
            opd[:, :, i] = sp.ndimage.filters.gaussian_filter(opd[:, :, i], Sigma, mode='reflect')

        # Try to account for decreased sensitivity at higher opd. Amplify higher OPD signal. This is also vital and it's not clear what the exponent should be, they all give different results.
        print("Adjusting OPD signal")
        opd = opd * (opdIndex[None, None, :] ** 0.5)

        opdSum = opd[:, :, ::-1].cumsum(axis=2)[:, :, ::-1]  # Cumulative sum of spectra from high to low opd. This way all pixels inside the cell should be higher values than outside the cell.
        bgSpec = opdSum[mask]  # The signals of the background regions.
        bgSpec = bgSpec.mean(axis=0)  # The average background signal
        opdSum = opdSum - bgSpec[None, None, :]  # Subtract the average background noise from all spectra.

        del opd, bgSpec
        snake = termSeg(opdSum, smoothing=1, lambda2=2, init_level_set=level_set)
        del opdSum
        print("smoothing")
        snake2 = morphSmoothing3D(snake, 5)

        return snake, snake2, opdIndex
    except Exception as e:
        return e


if __name__ == '__main__':
    read = True  # If this is true then we will load result from a previous run and plot them. If False then just run the code and save the results.
    pickleName = r'C:\Users\backman05\Desktop\findsurface\ac9.pickle'  # This is the filename for the results to be saved/loaded from

    if read:
        with open(pickleName, 'rb') as f:
            out = pickle.load(f)

        for i in out:
            if isinstance(i, Exception):
                print(i)
                continue
            snake, smoothed, opdIndex = i

            # Convert from OPD to microns
            height = volume3Dto2D(snake, opdIndex)  # Condense the 3d bool array to a 2d height map
            height = height / 2 / 1.37

            fig, ax = plt.subplots()
            im = plt.imshow(height, cmap='nipy_spectral', clim=[0, 7])
            ax.set_axis_off()
            cbar = plt.colorbar()
            cbar.ax.set_ylabel('microns', rotation=270)
            fig.show()



            # height = volume3Dto2D(smoothed, opdIndex)
            # plt.figure()
            # plt.imshow(height)

            # dx = 0.13 # This is the pixel size. We use this to plot XYZ with equal scaling
            #
            # x, y = np.arange(snake.shape[1]) * dx, np.arange(snake.shape[0]) * dx
            #
            # fig = plt.figure()  # 3D plot
            # ax = fig.add_subplot(projection='3d')
            # equalAxis3dPlot(x, y, height, ax)
            # contour = ax.contourf(x, y, height, levels=50, cmap=cm.nipy_spectral)
            # fig.show()
            # plt.colorbar(contour)

            # #Better looking, poor performance
            # fig = plt.figure()
            # ax = fig.add_subplot(projection='3d')
            # equalAxis3dPlot(x, y, height, ax)
            # X, Y = np.meshgrid(x, y)
            # ax.plot_surface(X, Y, height, cstride=5, rstride=5, cmap=cm.coolwarm)
            # fig.show()
        plt.show()
    else:
        files = glob(os.path.join(r'G:\Data\NA_i_vs_NA_c\matchedNAi_largeNAc\cells', "Cell*"))  # Find all acquisitions in the folder
        with mp.Pool(4) as p:
            out = p.starmap(seg, [(f,) for f in files])  # Run seg for each file, run in parallel for much faster completion.

        with open(pickleName, 'wb') as f:  # Save the results.
            pickle.dump(out, f)


