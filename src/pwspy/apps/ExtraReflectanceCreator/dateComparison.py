# -*- coding: utf-8 -*-
"""
Created on Tue Nov 20 13:13:34 2018

@author: backman05
"""


from pwspy import ImCube, CameraCorrection
from pwspy.utility import loadAndProcess
from pwspy.apps.ExtraReflectanceCreator.extraReflectance import plotExtraReflection , reflectanceHelper
from glob import glob
import numpy as np
import matplotlib.pyplot as plt
import os
import random
import matplotlib.animation as animation



def processIm(im):
    im.correctCameraEffects(CameraCorrection(100))
#    im.subtractDarkCounts(2000)
#    im.data = np.polynomial.polynomial.polyval(im.data, [0, 0.977241216, 1.73E-06, 1.70E-11]) #LCPWS 1 linearization
    im.normalizeByExposure()
    return im

#%%

if __name__ == '__main__':
    __spec__ = None
    materials = ['air','water', 'ipa','ethanol']
    rootDir = r'G:\Calibrations\4matExtraReflection\STORM'
    folders = glob(os.path.join(rootDir,'*'))
    dates = [os.path.split(f)[-1] for f in folders]
#    mat2Cell = {'air':[5,6],
#                'water':[3,4],
#                'ethanol':[1,2],
#                'ipa':[7,8]}
    mat2Cell = {'air':[6],
                'water':[4],
                'ethanol':[2],
                'ipa':[8]}
    
    fileDict = {m:{folder:glob(os.path.join(rootDir, folder, f'Cell{mat2Cell[m]}')) for folder in dates} for m in materials}
    cubes = loadAndProcess(fileDict, processIm, specifierNames = ['material', 'date'], parallel = True)
    print("Select an ROI")
    mask = random.choice(cubes).selectLassoROI()
    anis=[]
    for mat in materials:
        c = [im for im in cubes if im.material == mat]
        fig, ax = plt.subplots()
        fig.suptitle(mat)
        fig2, ax2 = plt.subplots()
        fig2.suptitle(mat)
        anims=[]
        for im in c:
            spectra = im.getMeanSpectra(mask)[0]
            ax.plot(im.wavelengths, spectra, label=im.date)
            anims.append((ax2.imshow(im.data.mean(axis=2), animated=True, clim=[np.percentile(im.data,.5),np.percentile(im.data,99.5)]), ax2.text(200,100,im.date)))
        ax.legend()
        anis.append(animation.ArtistAnimation(fig2, anims, interval=1000, blit=False))