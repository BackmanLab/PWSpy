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

    # rootDir = r'H:\Data\NA_i_vs_NA_c\matchedNAi_largeNAc\cells'
    rootDir = r'H:\Data\NA_i_vs_NA_c\smallNAi_largeNAc\cells'
    anName = 'p0'
    sigma = .5 # Blur radius in microns
    opdCutoffLow = 3
    opdCutoffHigh = 30

    files = glob(os.path.join(rootDir, 'Cell*'))
    acqs = [AcqDir(f) for f in files]

    # acqs = acqs[1:]#Skip acq 1

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
            artists = []
            for i in range(100):
                x, y = np.random.randint(0, opd.shape[1]), np.random.randint(0, opd.shape[0])
                lines = ax.plot(opdIndex, opd[y, x, :])
                vlines = ax.vlines(opdIndex[arr[y, x, :]], ymin=0, ymax=opd[y, x, :].max())
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
            temp = morph.binary_dilation(arr3[:,:,i])
            arr4[:,:,i] = morph.skeletonize(temp)

        #Estimate an OPD distance for each pixel
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

        #Detect a mesh. This would work a lot better if we could fill in the countours that we find.
        # verts, faces, normals, values = meas.marching_cubes_lewiner(arr4)
        # verts = verts.astype(int)
        # arr5 = np.zeros_like(arr4)
        # coords = (verts[:, 0], verts[:, 1], verts[:,2])
        # arr5[coords] = True
        #
        # fig = plt.figure(figsize=(10, 10))
        # ax = fig.add_subplot(111, projection='3d')
        # # Fancy indexing: `verts[faces]` to generate a collection of triangles
        # mesh = Poly3DCollection(verts[faces])
        # mesh.set_edgecolor('k')
        # ax.add_collection3d(mesh)
        # ax.set_xlim(0, arr.shape[1])
        # ax.set_ylim(0, arr.shape[0])
        # ax.set_zlim(0, arr.shape[2])


        plt.figure()
        _ = height.copy()
        _[np.isnan(_)]=0  # The nans don't plot very well
        plt.imshow(_)

        plt.figure()
        plt.imshow(Z)

        # from mpl_toolkits.mplot3d import Axes3D
        # from matplotlib import cm
        # fig = plt.figure()
        # ax = fig.add_subplot(111, projection='3d')
        # surf = ax.plot_surface(X, Y, Z, cmap=cm.coolwarm,linewidth=0, antialiased=False)

        # fig = plt.figure()
        # ax = fig.add_subplot(111, projection='3d')
        # cset = ax.contour(X, Y, Z, cmap=cm.coolwarm, stride=3)

        # fig = plt.figure()
        # ax = fig.add_subplot(111, projection='3d')
        # ax.plot_wireframe(X, Y, Z)

        # fig = plt.figure()
        # ax = fig.add_subplot(111, projection='3d')
        # ax.plot_surface(X, Y, Z, rstride=8, cstride=8, alpha=0.3)
        # cset = ax.contour(X, Y, Z, zdir='z', offset=-100, cmap=cm.coolwarm)
        # cset = ax.contour(X, Y, Z, zdir='x', offset=-40, cmap=cm.coolwarm)
        # cset = ax.contour(X, Y, Z, zdir='y', offset=40, cmap=cm.coolwarm)

        print("Done")
        a = 1  # debug here