if __name__ == '__main__':


    from pwspy.dataTypes import KCube, AcqDir
    from pwspy.analysis.pws import PWSAnalysisResults
    from glob import glob
    import os
    import scipy as sp
    import numpy as np
    from pwspy.utility.plotting import PlotNd
    import matplotlib.pyplot as plt
    import skimage.morphology as morph
    import skimage.measure as meas

    rootDir = r'H:\Data\NA_i_vs_NA_c\matchedNAi_largeNAc\cells'
    anName = 'p0'
    sigma = .5 # Blur radius in microns
    opdCutoffLow = 3
    opdCutoffHigh = 30
    minRMS = 0.08

    files = glob(os.path.join(rootDir, 'Cell*'))
    acqs = [AcqDir(f) for f in files]
    for acq in acqs:
        an = acq.pws.loadAnalysis(anName)
        refl = an.reflectance

        # Get a despeckled mask of where rms exceeds the threshold
        rmsMask = np.ones_like(an.rms, dtype=bool)
        # rmsMask = an.rms > minRMS
        # structure = morph.disk(2)
        # rmsMask = morph.binary_opening(rmsMask, structure)
        # rmsMask = morph.binary_closing(rmsMask, structure)


        opd, opdIndex = refl.getOpd(isHannWindow=True)  # Using the Hann window should improve dynamic range and reduce false peaks from frequency leakage.

        # Remove the low OPD signal.
        idxLow = np.argmin(np.abs(opdIndex - opdCutoffLow))
        idxHigh = np.argmin(np.abs(opdIndex - opdCutoffHigh))
        opd = opd[:, :, idxLow:idxHigh]
        opdIndex = opdIndex[idxLow:idxHigh]

        # Blur laterally to denoise
        sigma = sigma / acq.pws.pixelSizeUm  # convert from microns to pixels
        for i in range(opd.shape[2]):
            opd[:, :, i] = sp.ndimage.filters.gaussian_filter(opd[:, :, i], sigma, mode='reflect')

        arr = np.zeros_like(opd, dtype=bool)
        for i in range(opd.shape[0]):
            for j in range(opd.shape[1]):
                if rmsMask[i, j]: #Only process if rms was above the threshold here.
                    peaks, properties = sp.signal.find_peaks(opd[i, j, :])  # TODO vectorize? use kwargs?
                    arr[i, j, :][peaks] = True

        #3d morphology
        ball = morph.ball(1)
        arr2 = morph.binary_dilation(arr, ball)
        arr3 = meas.label(arr2)
        properties = meas.regionprops(arr3)
        #TODO remove regions that are too small. then dilate, skelotonize.

        # plt.imshow(rmsMask)
        # plt.show(block=False)
        a = 1  # debug here