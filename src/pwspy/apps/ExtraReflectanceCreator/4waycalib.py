# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 13:13:34 2018

@author: backman05
"""


from pwspy import ImCube, CameraCorrection
from pwspy.utility import loadAndProcess, reflectanceHelper, PlotNd
from pwspy.utility.reflection import plotExtraReflection , saveRExtra
from glob import glob
import numpy as np
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_pdf import PdfPages



def processIm(q):
    im = q.get()
    im.correctCameraEffects(CameraCorrection(100))
#    im.subtractDarkCounts(2000)
#    im.data = np.polynomial.polynomial.polyval(im.data, [0, 0.977241216, 1.73E-06, 1.70E-11]) #LCPWS 1 linearization
    im.normalizeByExposure()
    return im

#%%

if __name__ == '__main__':
    __spec__ = None
    
    
    exclude = []#[('water','ipa'),('water','ethanol'), ('ipa','ethanol'), ('ipa','air'), ('ethanol','air')]
    rootDir = r'G:\Calibrations\4matExtraReflection\LCPWS2_100xpfs\1_24_2019'
    produceRextraCube = True
    plotResults = False
    settings = ['none']
    mat2Cell = {'air':[5,6],
                'water':[3,4],
                'ethanol':[1,2],
                'ipa':[7,8]}
#    mat2Cell = {'air':[6],
#                'water':[4],
#                'ethanol':[2],
#                'ipa':[8]}
    
    
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
    
    fileDict = {m:{s:glob(os.path.join(rootDir,f'Cell{mat2Cell[m]}')) for s in settings} for m in materials}
    cubes = loadAndProcess(fileDict, processIm, specifierNames = ['material', 'setting'], parallel = True)
    for i, c in enumerate(cubes):
        print(f"Filtering {i+1}")
        c.filterDust(6)
    

    if plotResults:
        means, allCombos = plotExtraReflection(cubes, plotReflectionImages=False, excludedCombos = exclude) 
        with PdfPages(os.path.join(rootDir, "figs.pdf")) as pp:
            for i in plt.get_fignums():
                f = plt.figure(i)
                f.set_size_inches(9,9)
                pp.savefig(f)
    if produceRextraCube:
        rextras = saveRExtra(cubes)
        plot = PlotNd(rextras['mean'], ['y','x','lambda'])
        np.save(os.path.join(rootDir,'rextra.npy'),rextras['mean'].astype(np.float32))


#            
#            
#Todo: plot I0