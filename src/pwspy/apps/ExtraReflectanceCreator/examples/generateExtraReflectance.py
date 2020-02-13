# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 13:13:34 2018

@author: Nick Anthony

Based off of pwspy.apps.ExtraReflectanceCreator.examples.4waycalib.py"""

from pwspy.utility.fileIO import loadAndProcess
from pwspy.utility.reflection import reflectanceHelper
import pwspy.utility.reflection.extraReflectance as er
from pwspy.dataTypes import Roi
from glob import glob
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import random

from pwspy.moduleConsts import Material


def processIm(im):
    im.correctCameraEffects()
    im.normalizeByExposure()
    im.filterDust(.75)
    return im


if __name__ == '__main__':
    __spec__ = None  # This is sometimes needed for multiprocessing to work on windows.
    plt.ion()

    rootDir = r'G:\Aya_NAstudy'
    produceRextraCube = False  # Do you want to actually save the file?
    plotResults = True  # Do you want to plot information about the calibration?

    materials = [('air', Material.Air), ('water', Material.Water)]  # Map folder names to a "pwspy.moduleConsts.Material" value
    settings = [os.path.split(f)[-1] for f in glob(os.path.join(rootDir, '*')) if os.path.exists(os.path.join(f, 'er'))]  # Determine which settings are available by scanning the folders

    fig, axes = plt.subplots(ncols=2)
    axes[0].set_ylabel('n')
    axes[0].set_xlabel('nm')
    axes[0].set_title("Index of Refraction")
    axes[1].set_ylabel('reflectance')
    axes[1].set_xlabel('nm')
    axes[1].set_title("Glass Interface Reflectance")
    [axes[0].plot(reflectanceHelper.n.index, reflectanceHelper.n[mat]['n'], label=matName) for matName, mat in materials]
    axes[0].legend()
    [axes[1].plot(reflectanceHelper.getReflectance(mat, Material.Glass).index, reflectanceHelper.getReflectance(mat, Material.Glass), label=matName) for
     matName, mat in materials]
    axes[1].legend()

    fileFrame = pd.DataFrame([{'setting': setting, 'material': m[1], 'cube': cube} for setting in settings for m in materials for cube in glob(
        os.path.join(rootDir, setting, 'er', m[0],
                     'Cell*'))])  # Convert the folder structure to a dataframe labeled with NA setting, Material, and the ImCube objects.
    df = loadAndProcess(fileFrame, processIm, parallel=True)  # Returns a dataframe matching the form of `fileFrame` except the filepaths have been replaced with ImCube objects (The filepaths have been loaded and processed using the `processIms` function.).

    theoryR = er.getTheoreticalReflectances(list(zip(*materials))[1], df['cube'][0].wavelengths, 0.52)
    matCombos = er.generateMaterialCombos(list(zip(*materials))[1])
    if plotResults:
        verts = random.choice(df['cube']).selectLassoROI()
        roi = Roi.fromVerts('plottingArea', 1, verts, df['cube'][0].data.shape[:2])
        er.plotExtraReflection(df, theoryR, matCombos, 0.52, roi, plotReflectionImages=False)
        with PdfPages(os.path.join(rootDir, "figs.pdf")) as pp:
            for i in plt.get_fignums():
                f = plt.figure(i)
                f.set_size_inches(9, 9)
                pp.savefig(f)
    if produceRextraCube:
        for sett in set(df['setting']):
            allCombos = er.getAllCubeCombos(matCombos, df[df['setting'] == sett])
            erCube, rextras, plots = er.generateRExtraCubes(allCombos, theoryR, 0.52)
            erCube.toHdfFile(rootDir, f'rextra_{sett}')
