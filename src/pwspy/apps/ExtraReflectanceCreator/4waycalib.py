# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 13:13:34 2018

@author: backman05
"""


from pwspy import ImCube, CameraCorrection
from pwspy.utility import loadAndProcess, reflectanceHelper, PlotNd
from pwspy.apps.ExtraReflectanceCreator.extraReflectance import plotExtraReflection , saveRExtra, prepareData
from glob import glob
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd



def processIm(im):
    im.correctCameraEffects(CameraCorrection(100))
#    im.subtractDarkCounts(2000)
#    im.data = np.polynomial.polynomial.polyval(im.data, [0, 0.977241216, 1.73E-06, 1.70E-11]) #LCPWS 1 linearization
    im.normalizeByExposure()
    return im

#%%

if __name__ == '__main__':
    __spec__ = None
    plt.interactive(True)
    
    exclude = []#[('water','ipa'),('water','ethanol'), ('ipa','ethanol'), ('ipa','air'), ('ethanol','air')]
    rootDir = r'G:\Calibrations\4matExtraReflection\LCPWS2_100xpfs\1_24_2019'
    produceRextraCube = True
    plotResults = False
    settings = ['none']
    
    
    materials = ['air','water', 'ipa','ethanol']
    
    fig, axes = plt.subplots(ncols=2)
    axes[0].set_ylabel('n')
    axes[0].set_xlabel('nm')
    axes[0].set_title("Index of Refraction")
    axes[1].set_ylabel('reflectance')
    axes[1].set_xlabel('nm')
    axes[1].set_title("Glass Interface Reflectance")
    [axes[0].plot(reflectanceHelper.n.index,reflectanceHelper.n[mat]['n'], label = mat) for mat in materials]
    axes[0].legend()
    [axes[1].plot(reflectanceHelper.getReflectance(mat, 'glass').index, reflectanceHelper.getReflectance(mat,'glass'), label=mat) for mat in materials]
    axes[1].legend()
    
    fileFrame = pd.DataFrame([{'setting': None, 'material': m, 'cubes': cube} for m in materials for cube in glob(os.path.join(rootDir,m,'Cell*'))])
    cubes = loadAndProcess(fileFrame, processIm, parallel=True)
    for i, c in enumerate(cubes['cubes']):
        print(f"Filtering {i+1}")
        c.filterDust(6)

    meanValues, allCombos, theoryR, matCombos, settings = prepareData(cubes, excludedCombos=exclude)
    if plotResults:
        means, allCombos = plotExtraReflection(allCombos, meanValues, theoryR, matCombos, settings, plotReflectionImages=False)
        with PdfPages(os.path.join(rootDir, "figs.pdf")) as pp:
            for i in plt.get_fignums():
                f = plt.figure(i)
                f.set_size_inches(9, 9)
                pp.savefig(f)
    if produceRextraCube:
        rextras = saveRExtra(allCombos, theoryR, matCombos)
        plot = PlotNd(rextras['mean'], ['y', 'x', 'lambda'])
        np.save(os.path.join(rootDir,'rextra.npy'), rextras['mean'].data.astype(np.float32))

    plt.show(block=True)
#            
#            
#Todo: plot I0