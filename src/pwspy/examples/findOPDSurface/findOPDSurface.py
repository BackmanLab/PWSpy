

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
    import skan
    from pwspy.examples.findOPDSurface.funcs import prune3dIm, Skel

    # rootDir = r'G:\Data\NA_i_vs_NA_c\matchedNAi_largeNAc\cells'
    rootDir = r'G:\Data\NA_i_vs_NA_c\smallNAi_largeNAc\cells'
    anName = 'p0'
    roiName = 'cell'
    sigma = .5  # Blur radius in microns. greater sigma generally leads to greater sensitivity, with more contiguous regions of detected peaks. Also greater noise though.
    opdCutoffLow = 3
    opdCutoffHigh = 20

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

        # Blur laterally to denoise. This step is vital
        Sigma = sigma / acq.pws.pixelSizeUm  # convert from microns to pixels
        for i in range(opd.shape[2]):
            opd[:, :, i] = sp.ndimage.filters.gaussian_filter(opd[:, :, i], Sigma, mode='reflect')

        #Try to account for decreased sensitivity at higher opd
        print("Adjusting OPD signal")
        opd = opd * (opdIndex[None, None, :] ** 0.5)

        print("Detect Peaks")
        arr = np.zeros_like(opd, dtype=bool)
        for i in range(opd.shape[0]):
            for j in range(opd.shape[1]):
                peaks, properties = sp.signal.find_peaks(opd[i, j, :])  # TODO vectorize? use kwargs?
                arr[i, j, :][peaks] = True



        if True: # plotPeakDetection
            print("Plotting random peaks")
            fig, ax = plt.subplots()
            plt.xlabel("OPD (um)")
            artists = []
            for i in range(100):
                x, y = np.random.randint(0, opd.shape[1]), np.random.randint(0, opd.shape[0])
                lines = ax.plot(opdIndex, opd[y, x, :])
                vlines = ax.vlines(opdIndex[arr[y, x, :]], ymin=opd[y, x, :].min(), ymax=opd[y, x, :].max())
                artists.append(lines + [vlines])
            mp = MultiPlot(artists, "Peak Detection")
            mp.show()

        #2d regions
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
            disk = morph.disk(3)
            temp = morph.binary_dilation(arr3[:, :, i], disk)
            arr4[:, :, i] = morph.skeletonize(temp)

        print("analyze skeleton 2d")
        arr5 = prune3dIm(arr4)


        #3d regions
        print("Remove regions. 3D")
        arr6 = np.zeros_like(arr5)
        _ = morph.binary_dilation(arr5)
        labeled = meas.label(_)
        properties = meas.regionprops(labeled)
        for prop in properties:
            if prop.area > 1e4:
                coords = prop.coords
                coords = (coords[:, 0], coords[:, 1], coords[:,2])
                arr6[coords] = True
        arr6 = morph.skeletonize(arr6)

        s = Skel(arr6)

        #Estimate an OPD distance for each pixel. This is too slow.
        print("Condense to 2d")
        height = np.zeros((arr6.shape[0], arr6.shape[1]))
        for i in range(arr6.shape[0]):
            for j in range(arr6.shape[1]):
                where = np.argwhere(arr6[i, j, :]).squeeze()
                if where.shape == (0,):
                    height[i, j] = np.nan
                else:
                    height[i, j] = opdIndex[where].max()

        print("Interpolate")
        # Interpolate out the Nans
        def interpolateNans(arr, method='linear'):  # 'cubic' may also be good.
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
            Z = griddata(coords, Zna.flatten(), icoords, method=method)
            Z[np.isnan(Z)] = 0
            Z = Z.reshape(arr.shape)

            return Z

        Z = interpolateNans(height, method='linear')

        print("Plot")
        p = PlotNd(opd, extraDimIndices=[opdIndex], names=('y','x','opd'))
        p2 = PlotNd(arr, extraDimIndices=[opdIndex], names=('y','x','opd'))
        # p3 = PlotNd(arr2, extraDimIndices=[opdIndex])
        p4 = PlotNd(arr3, extraDimIndices=[opdIndex], names=('y','x','opd'))
        p5 = PlotNd(arr4, extraDimIndices=[opdIndex], names=('y','x','opd'))
        p6 = PlotNd(arr5, extraDimIndices=[opdIndex], names=('y','x','opd'))
        p7 = PlotNd(arr6, extraDimIndices=[opdIndex], names=('y','x','opd'))


        fig = plt.figure()
        plt.imshow(an.meanReflectance, cmap='gray', clim=[np.percentile(an.meanReflectance, 1), np.percentile(an.meanReflectance, 99)])
        fig.show()

        fig = plt.figure()
        _ = height.copy()
        _[np.isnan(_)]=0  # The nans don't plot very well
        plt.imshow(_, cmap='jet', clim=[_.min(), np.percentile(_,99)])
        plt.colorbar()
        fig.show()

        s.plot()

        fig = plt.figure()
        _ = Z.copy()
        _[_==0] = np.percentile(_[_!=0], .1)
        plt.imshow(_)
        plt.colorbar()
        plt.title("Simple Interpolation.")
        fig.show()


        print("Done")
        a = 1  # debug here