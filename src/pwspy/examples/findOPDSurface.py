if __name__ == '__main__':


    from pwspy.dataTypes import KCube, AcqDir
    from pwspy.analysis.pws import PWSAnalysisResults
    from glob import glob
    import os
    import scipy as sp
    import numpy as np
    from pwspy.utility.plotting import PlotNd, MultiPlot
    import matplotlib.pyplot as plt
    import skimage.morphology as morph
    import skimage.measure as meas

    # rootDir = r'H:\Data\NA_i_vs_NA_c\matchedNAi_largeNAc\cells'
    rootDir = r'H:\Data\NA_i_vs_NA_c\smallNAi_largeNAc\cells'
    anName = 'p0'
    sigma = .5 # Blur radius in microns
    opdCutoffLow = 3
    opdCutoffHigh = 20
    minRMS = 0.05
    minRegion = 5000

    files = glob(os.path.join(rootDir, 'Cell*'))
    acqs = [AcqDir(f) for f in files]
    for acq in acqs:
        an = acq.pws.loadAnalysis(anName)
        refl = an.reflectance

        opd, opdIndex = refl.getOpd(isHannWindow=True)  # Using the Hann window should improve dynamic range and reduce false peaks from frequency leakage.

        # A mask to remove low rms regions
        rmsMask = np.ones_like(an.rms, dtype=bool)
        # rmsMask = an.rms > minRMS
        # disk = morph.disk(2)
        # rmsMask = morph.binary_opening(rmsMask, disk)
        # disk = morph.disk(4)
        # rmsMask = morph.binary_closing(rmsMask, disk)

        # Remove the low OPD signal.
        idxLow = np.argmin(np.abs(opdIndex - opdCutoffLow))
        idxHigh = np.argmin(np.abs(opdIndex - opdCutoffHigh))
        opd = opd[:, :, idxLow:idxHigh]
        opdIndex = opdIndex[idxLow:idxHigh]

        # Blur laterally to denoise
        sigma = sigma / acq.pws.pixelSizeUm  # convert from microns to pixels
        for i in range(opd.shape[2]):
            opd[:, :, i] = sp.ndimage.filters.gaussian_filter(opd[:, :, i], sigma, mode='reflect')

        print("Detect Peaks")
        arr = np.zeros_like(opd, dtype=bool)
        for i in range(opd.shape[0]):
            for j in range(opd.shape[1]):
                if rmsMask[i, j]:
                    peaks, properties = sp.signal.find_peaks(opd[i, j, :])  # TODO vectorize? use kwargs?
                    arr[i, j, :][peaks] = True


        if True: # plotPeakDetection
            print("Plotting random peaks")
            fig, ax = plt.subplots()
            artists = []
            for i in range(100):
                x, y = np.random.randint(0, opd.shape[1]), np.random.randint(0, opd.shape[0])
                lines = ax.plot(opdIndex, opd[y, x, :])
                vlines = ax.vlines(opdIndex[arr[y, x, :]], ymin=0, ymax=opd[y, x, :].max())
                artists.append(lines + [vlines])
            mp = MultiPlot(artists, "G")
            mp.show()


        #3d morphology
        print("Begin morphology")
        disk = morph.disk(1) # Doing a ball just removed everything.
        arr2 = morph.binary_opening(arr, disk[:,:,None]) #Get rid of specks
        arr4 = np.zeros_like(arr2, dtype=bool)
        arr5 = np.zeros_like(arr2, dtype=int)
        arr3 = meas.label(arr2)
        print("Measure properties")
        properties = meas.regionprops(arr3)
        for prop in properties:  # Remove small regions
            coords = prop.coords
            coords = (coords[:, 0], coords[:, 1], coords[:, 2])
            arr5[coords] = prop.area
            if prop.area > minRegion:
                arr4[coords] = True
        #TODO remove regions that are too small. then dilate, skelotonize. Actually need ot improve peak detection.

        print("Done")
        a = 1  # debug here