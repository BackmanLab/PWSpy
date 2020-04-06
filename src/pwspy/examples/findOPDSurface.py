

if __name__ == '__main__':
    from pwspy.dataTypes import AcqDir
    from glob import glob
    import os
    import scipy as sp
    import numpy as np
    from pwspy.utility.plotting import PlotNd, MultiPlot
    import matplotlib.pyplot as plt
    import skimage.morphology as morph
    import skimage.measure as meas
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    import pandas as pd
    import skan
    from PyQt5.QtWidgets import QTableView
    from pwspy.apps.sharedWidgets.extraReflectionManager._ERUploaderWindow import PandasModel

    # rootDir = r'H:\Data\NA_i_vs_NA_c\matchedNAi_largeNAc\cells'
    rootDir = r'H:\Data\NA_i_vs_NA_c\smallNAi_largeNAc\cells'
    anName = 'p0'
    roiName = 'cell'
    sigma = .5 # Blur radius in microns
    opdCutoffLow = 3
    opdCutoffHigh = 30

    files = glob(os.path.join(rootDir, 'Cell*'))
    acqs = [AcqDir(f) for f in files]


    for acq in acqs:
        try:
            an = acq.pws.loadAnalysis(anName)
        except OSError:
            print("No analysis found. skipping")
            continue

        opd, opdIndex = an.reflectance.getOpd(isHannWindow=True)  # Using the Hann window should improve dynamic range and reduce false peaks from frequency leakage.

        # Remove the low OPD signal.
        idxLow = np.argmin(np.abs(opdIndex - opdCutoffLow))
        idxHigh = np.argmin(np.abs(opdIndex - opdCutoffHigh))
        opd = opd[:, :, idxLow:idxHigh]
        opdIndex = opdIndex[idxLow:idxHigh]

        # Blur laterally to denoise
        Sigma = sigma / acq.pws.pixelSizeUm  # convert from microns to pixels
        for i in range(opd.shape[2]):
            opd[:, :, i] = sp.ndimage.filters.gaussian_filter(opd[:, :, i], Sigma, mode='reflect')

        #Try to account for decreased sensitivity at higher opd
        print("Adjusting OPD signal")
        opd = opd * (opdIndex[None, None, :] ** 0.5)
        # filterCutoff = .01
        # sampleFreq = (len(opdIndex) - 1) / (opdIndex[-1] - opdIndex[0])
        # import scipy.signal as sps
        # b, a = sps.butter(2, filterCutoff, btype='highpass', fs=sampleFreq)  # Generate the filter coefficients
        # opd = sps.filtfilt(b, a, opd, axis=2).astype(opd.dtype)  # Actually do the filtering on the data.


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
                vlines = ax.vlines(opdIndex[arr[y, x, :]], ymin=opd[y,x,:].min(), ymax=opd[y, x, :].max())
                artists.append(lines + [vlines])
            mp = MultiPlot(artists, "Peak Detection")
            mp.show()

        #2d regions #TODO analyze skeleton lengths to remove stuff. skan
        print("Remove regions. 2D")
        arr2 = np.zeros_like(arr)
        for i in range(arr.shape[2]):
            labeled = meas.label(arr[:, :, i])
            properties = meas.regionprops(labeled)
            for prop in properties:
                if prop.area > 30:
                    coords = prop.coords
                    coords = (coords[:, 0], coords[:, 1], i)
                    arr2[coords] = True

        #3d regions
        print("Remove regions. 3D")
        arr3 = np.zeros_like(arr2)
        labeled = meas.label(arr2)
        properties = meas.regionprops(labeled)
        for prop in properties:
            if prop.area > 1e3:
                coords = prop.coords
                coords = (coords[:, 0], coords[:, 1], coords[:,2])
                arr3[coords] = True

        print("Skeletonize. 2D")
        arr4 = np.zeros_like(arr3)  # 3d skeletonizing didn't work well.
        for i in range(arr3.shape[2]):
            temp = morph.binary_dilation(arr3[:,:,i])
            arr4[:,:,i] = morph.skeletonize(temp)

        print("analyze skeleton 2d")
        skels = []
        for i in range(arr4.shape[2]):
            if arr4[:, :, i].sum() == 0:  # nothing to be done if the frame is empty
                skels.append(None)
            else:
                s = skan.Skeleton(arr4[:, :, i])
                plt.figure()
                for n in range(s.n_paths):
                    coords = s.path_coordinates(n)
                    coords = (coords[:, 0], coords[:, 1])
                    plt.plot(*coords)
                stats = skan.summarize(s)
                #The types are: - tip-tip (0) - tip-junction (1) - junction-junction (2) - path-path (3)
                for id in range(max((stats['epId1'].max(), stats['epId2'].max()))+1):
                    b = stats.apply(lambda row: id in row['eps'], axis=1)
                    a = stats[b]  # Select all rows using this endpoint
                    if len(a) > 1: #multiple branches use this endpoint.
                        if 2 in a.type.unique() or 3 in a.type.unique():
                            idxes = a[a.type < 2].index
                            stats = stats.drop(idxes, axis=0)
                        else:
                            #delete the shortest one
                            idx = a.length.idxmin()
                            stats = stats.drop(idx, axis=0)
                skels.append(s)
                plt.figure()
                for n in stats.index:
                    coords = s.path_coordinates(n)
                    coords = (coords[:, 0], coords[:, 1])
                    plt.plot(*coords)

        skel = skan.Skeleton(arr4)
        stats = skan.branch_statistics(skel.graph)
        df = skan.summarize(skel)
        pm = PandasModel(df)
        qt = QTableView()
        qt.setModel(pm)
        qt.setSortingEnabled(True)
        qt.show()

        arr6 = np.zeros_like(arr)
        for i in range(skel.n_paths):
            coords = skel.path_coordinates(i)

        #Estimate an OPD distance for each pixel. This is too slow.
        print("Condense to 2d")
        height = np.zeros((arr4.shape[0], arr4.shape[1]))
        for i in range(arr4.shape[0]):
            for j in range(arr4.shape[1]):
                where = np.argwhere(arr4[i, j, :]).squeeze()
                if where.shape == (0,):
                    height[i, j] = np.nan
                else:
                    height[i, j] = opdIndex[where].mean()

        print("Interpolate")
        # Interpolate out the Nans
        def interpolateNans(arr):
            """Interpolate out nan values along the third axis of an array"""
            from scipy.interpolate import interp2d, griddata
            x, y = list(range(arr.shape[1])), list(range(arr.shape[0]))
            X, Y = np.meshgrid(x, y)
            nans = np.isnan(arr)
            Xna = X[~nans]
            Yna = Y[~nans]
            Zna = arr[~nans]

            coords = np.array(list(zip(Xna.flatten(), Yna.flatten())))
            icoords = np.array(list(zip(X.flatten(), Y.flatten())))
            Z = griddata(coords, Zna.flatten(), icoords, method='linear')  # 'cubic' may also be good.
            Z[np.isnan(Z)] = 0
            Z = Z.reshape(arr.shape)

            return Z

        Z = interpolateNans(height)

        print("Plot")
        p = PlotNd(opd, extraDimIndices=[opdIndex])
        p2 = PlotNd(arr, extraDimIndices=[opdIndex])
        p3 = PlotNd(arr2, extraDimIndices=[opdIndex])
        p4 = PlotNd(arr3, extraDimIndices=[opdIndex])
        p5 = PlotNd(arr4, extraDimIndices=[opdIndex])


        fig = plt.figure()
        plt.imshow(an.meanReflectance)
        fig.show()

        fig = plt.figure()
        _ = height.copy()
        _[np.isnan(_)]=0  # The nans don't plot very well
        plt.imshow(_)
        fig.show()

        fig = plt.figure()
        plt.imshow(Z)
        fig.show()


        print("Done")
        a = 1  # debug here