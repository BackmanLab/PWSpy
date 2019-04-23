# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 13:13:34 2018

@author: backman05
"""


from pwspy import ImCube, CameraCorrection
from pwspy.utility import loadAndProcess, reflectanceHelper, PlotNd
import pwspy.apps.ExtraReflectanceCreator.extraReflectance as er
from glob import glob
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import random

from pwspy.moduleConsts import Material


def processIm(im):
    im.correctCameraEffects(CameraCorrection(100))
#    im.subtractDarkCounts(2000)
#    im.data = np.polynomial.polynomial.polyval(im.data, [0, 0.977241216, 1.73E-06, 1.70E-11]) #LCPWS 1 linearization
    im.normalizeByExposure()
    im.filterDust(6)
    return im

#%%

if __name__ == '__main__':
    __spec__ = None
    plt.interactive(True)
    
    exclude = [(Material.Water, Material.Ipa), (Material.Water, Material.Ethanol)]
    rootDir = r'/home/nick/Desktop/4matExtraReflection/LCPWS1/1_23_2019'
    produceRextraCube = True
    plotResults = True
    
    materials = [('air', Material.Air), ('water', Material.Water), ('ipa', Material.Ipa), ('ethanol', Material.Ethanol)]
    
    fig, axes = plt.subplots(ncols=2)
    axes[0].set_ylabel('n')
    axes[0].set_xlabel('nm')
    axes[0].set_title("Index of Refraction")
    axes[1].set_ylabel('reflectance')
    axes[1].set_xlabel('nm')
    axes[1].set_title("Glass Interface Reflectance")
    [axes[0].plot(reflectanceHelper.n.index,reflectanceHelper.n[mat]['n'], label=matName) for matName, mat in materials]
    axes[0].legend()
    [axes[1].plot(reflectanceHelper.getReflectance(mat, Material.Glass).index, reflectanceHelper.getReflectance(mat, Material.Glass), label=matName) for matName, mat in materials]
    axes[1].legend()
    
    fileFrame = pd.DataFrame([{'setting': 'none', 'material': m, 'cube': cube} for m in materials for cube in glob(os.path.join(rootDir,m,'Cell*'))])
    cubes = loadAndProcess(fileFrame, processIm, parallel=True)

    theoryR = er.getTheoreticalReflectances(list(zip(*materials))[1], cubes['cube'][0].wavelengths)
    matCombos = er.generateMaterialCombos(list(zip(*materials))[1], excludedCombos=exclude)
    if plotResults:
        mask = random.choice(cubes['cube']).selectLassoRoi()
        er.plotExtraReflection(cubes, theoryR, matCombos, mask, plotReflectionImages=False)
        with PdfPages(os.path.join(rootDir, "figs.pdf")) as pp:
            for i in plt.get_fignums():
                f = plt.figure(i)
                f.set_size_inches(9, 9)
                pp.savefig(f)
    if produceRextraCube:
        for sett in set(cubes['setting']):
            allCombos = er.getAllCubeCombos(matCombos, cubes[cubes['setting']==sett])
            erCube, rextras, plots = er.generateRExtraCubes(allCombos, theoryR)
            erCube.toHdfFile(rootDir, f'rextra_{sett}')

#Todo: plot I0