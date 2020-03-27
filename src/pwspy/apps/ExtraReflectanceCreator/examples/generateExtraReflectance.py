# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 13:13:34 2018

@author: Nick Anthony

Based off of pwspy.apps.ExtraReflectanceCreator.examples.4waycalib.py"""

from pwspy.utility.fileIO import loadAndProcess
from pwspy.utility.reflection import reflectanceHelper, Material
import pwspy.utility.reflection.extraReflectance as er
from pwspy.dataTypes import Roi
from glob import glob
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import random


def processIm(im):
    im.correctCameraEffects()
    im.normalizeByExposure()
    print(im.metadata.filePath)
    print(im.metadata.exposure)
    im.filterDust(.75)
    return im


if __name__ == '__main__':
    __spec__ = None  # This is sometimes needed for multiprocessing to work on windows.
    plt.ion()

    rootDir = r'G:\Aya_NAstudy'
    produceRextraCube = False  # Do you want to actually save the file?
    plotResults = True  # Do you want to plot information about the calibration?

    materials = [('air', Material.Air), ('water', Material.Water)]  # Map folder names to a "pwspy.moduleConsts.Material" value
    settingsNADict = {0.5: ['matchedNAi_largeNAc', 'matchedNAi_smallNAc'],
                0.243: ['smallNAi_largeNAc', 'smallNAi_smallNAc']} #The folder names and NAi for each setting tested.

    for na in settingsNADict.keys():
        settings = settingsNADict[na]
        fig, axes = plt.subplots(ncols=2)
        axes[0].set_ylabel('n')
        axes[0].set_xlabel('nm')
        axes[0].set_title("Index of Refraction")
        axes[1].set_ylabel('reflectance')
        axes[1].set_xlabel('nm')
        axes[1].set_title(f"Glass Interface Reflectance. NA={na}")
        [axes[0].plot(reflectanceHelper._n.index, reflectanceHelper._n[mat]['n'], label=matName) for matName, mat in materials]
        axes[0].legend()
        for matName, mat in materials:
            r = reflectanceHelper.getReflectance(mat, Material.Glass, NA=na)
            axes[1].plot(r.index, r, label=matName)
        axes[1].legend()

        fileFrame = pd.DataFrame([{'setting': setting, 'material': m[1], 'cube': cube} for setting in settings for m in materials for cube in glob(
            os.path.join(rootDir, setting, 'er', m[0],'Cell*'))])  # Convert the folder structure to a dataframe labeled with NA setting, Material, and the ImCube objects.
        df = loadAndProcess(fileFrame, processIm, parallel=True)  # Returns a dataframe matching the form of `fileFrame` except the filepaths have been replaced with ImCube objects (The filepaths have been loaded and processed using the `processIms` function.).

        theoryR = er.getTheoreticalReflectances(list(zip(*materials))[1], df['cube'][0].wavelengths, numericalAperture=na)
        matCombos = er.generateMaterialCombos(list(zip(*materials))[1])
        if plotResults:
            verts = random.choice(df['cube']).selectLassoROI()
            roi = Roi.fromVerts('plottingArea', 1, verts, df['cube'][0].data.shape[:2])
            er.plotExtraReflection(df, theoryR, matCombos, na, roi, plotReflectionImages=False)
            with PdfPages(os.path.join(rootDir, "figs.pdf")) as pp:
                for i in plt.get_fignums():
                    f = plt.figure(i)
                    f.set_size_inches(9, 9)
                    pp.savefig(f)
        if produceRextraCube:
            for sett in set(df['setting']):
                allCombos = er.getAllCubeCombos(matCombos, df[df['setting'] == sett])
                erCube, rextras, plots = er.generateRExtraCubes(allCombos, theoryR, numericalAperture=na)
                erCube.toHdfFile(rootDir, f'rextra_{sett}')

    a = 1
