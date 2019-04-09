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
    materials = ['air','water', 'ipa','ethanol']
    rootDir = r'G:\Calibrations\4matExtraReflection\STORM'
    settings = [os.path.split(f)[-1] for f in glob(os.path.join(rootDir, '*'))]
    folders = glob(os.path.join(rootDir,'*'))
    dates = [os.path.split(f)[-1] for f in folders]

    fileFrame = pd.DataFrame([{'setting': s, 'material': m, 'cube': cube} for s in settings for m in materials for cube in glob(os.path.join(rootDir,s, m, 'Cell*'))])
    # fileDict = {m:{folder:glob(os.path.join(rootDir, folder, f'Cell{mat2Cell[m]}')) for folder in dates} for m in materials}
    cubes = loadAndProcess(fileFrame, processIm, parallel = True)
    print("Select an ROI")
    mask = random.choice(cubes).selectLassoROI()
    anis=[]
    for mat in materials:
        c = cubes[cubes['material'] == mat]
        # c = [im for im in cubes if im.material == mat]
        fig, ax = plt.subplots()
        fig.suptitle(mat)
        fig2, ax2 = plt.subplots()
        fig2.suptitle(mat)
        anims=[]
        for i, row in c.iterrows():
            im = row['cube']
            spectra = im.getMeanSpectra(mask)[0]
            ax.plot(im.wavelengths, spectra, label=row['setting'])
            anims.append((ax2.imshow(im.data.mean(axis=2), animated=True, clim=[np.percentile(im.data,.5),np.percentile(im.data,99.5)]), ax2.text(200,100,row['setting'])))
        ax.legend()
        anis.append(animation.ArtistAnimation(fig2, anims, interval=1000, blit=False))
