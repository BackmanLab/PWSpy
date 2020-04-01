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

    rootDir = r'H:\Data\NA_i_vs_NA_c\matchedNAi_largeNAc\cells'
    # rootDir = r'H:\Data\NA_i_vs_NA_c\smallNAi_largeNAc\cells'
    anName = 'p0'
    sigma = .5 # Blur radius in microns
    opdCutoffLow = 3
    opdCutoffHigh = 20

    files = glob(os.path.join(rootDir, 'Cell*'))
    acqs = [AcqDir(f) for f in files]
    for acq in acqs:
        an = acq.pws.loadAnalysis(anName)
        refl = an.reflectance

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

        #Try to account for decreased sensitivity at higher opd
        opd = opd * opdIndex[None, None, :]

        print("Detect Peaks")
        arr = np.zeros_like(opd, dtype=bool)
        for i in range(opd.shape[0]):
            for j in range(opd.shape[1]):
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


        #2d regions
        arr2 = np.zeros_like(arr)
        for i in range(arr.shape[2]):
            labeled = meas.label(arr[:,:,i])
            properties = meas.regionprops(labeled)
            print(i)
            for prop in properties:
                if prop.area > 30:
                    coords = prop.coords
                    coords = (coords[:, 0], coords[:, 1], i)
                    arr2[coords] = True

        #3d regions
        arr3 = np.zeros_like(arr2)
        labeled = meas.label(arr2)
        properties = meas.regionprops(labeled)
        for prop in properties:
            if prop.area > 1e3:
                coords = prop.coords
                coords = (coords[:, 0], coords[:, 1], coords[:, 2])
                arr3[coords] = True

        arr4 = np.zeros_like(arr3) # 3d skeletonizing didn't work well.
        for i in range(arr3.shape[2]):
            temp = morph.binary_dilation(arr3[:,:,i])
            arr4[:,:,i] = morph.skeletonize(temp)

        print("Done")
        a = 1  # debug here