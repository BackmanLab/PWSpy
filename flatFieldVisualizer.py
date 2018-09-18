# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pwspython import ImCube

#%%User Input

file = r'G:\Calibrations\LCPWS1\Cell6'
#%% Loading
theory = pd.read_csv('Reflectance-calcs.txt', delimiter = '\t', index_col = 0)   #The theoretical reflectance for a 1um thin film. silica on silicon.
theory = theory.loc[500:700:2]
silicon = pd.read_csv('SiliconProps.csv')
silicon = silicon.set_index(silicon['wavelength(nm)'])
sref = silicon["Reflection"]
#resample the reflectance to match the other data.
sref = sref.reindex(np.arange(sref.index.min(),sref.index.max()+1,1))
sref = sref.interpolate()
sref = sref.loc[500:700:2]

base = ImCube.fromOldPWS(file)
im = base
mirror = base.getMeanSpectra(base.selectROI())[0]
#Since our mirror in silicon adjust for the real reflectivity of silicon
mirror = mirror / sref

#%% Processing
im._data = np.apply_along_axis(lambda arr: np.divide(arr, mirror),axis=2, arr=im._data)
_ = np.array(theory).squeeze()
ztheory = (_ - _.mean())/(_.std() * _.shape[0])     #Zero normalize for correlation
zim = (im._data - im._data.mean(axis=2,keepdims = True)) / (im._data.std(axis=2, keepdims = True))  #zero normalize for correlation
corr = np.apply_along_axis(lambda arr: np.correlate(ztheory, arr ,mode = 'same'), axis = 2, arr = zim)

#%% Data Extraction
amp = im._data.max(axis = 2) - im._data.min(axis = 2)   #The amplitude of the spectra.
corramp = np.max(corr,axis=2)   #The strength of the correlation
corrmax = np.argmax(corr, axis = 2) #The shift in index that gives the strongest correlation.
minn = np.apply_along_axis(lambda arr: np.subtract(arr, np.array(theory).squeeze()), axis = 2, arr = im._data) #The difference between the minimum of the spectra and the theoretical minima. this indicates unwanted light.

#%% Plotting
fig,axs = plt.subplots(nrows = 2, ncols=2)
axs[0,0].imshow(amp)
axs[0,1].imshow(corrmax)
axs[1,1].imshow(corramp)
axs[1,0].imshow(minn)
while True:
    fig2, ax = plt.subplots()
    ax.plot(np.array(theory.index).astype(np.float), np.array(theory["Reflectance"]).astype(np.float), label="Theory")
    
    mean, std = im.getMeanSpectra(im.selectROI())
    ax.plot(im.wavelengths,mean, label = "Data")
    ax.fill_between(im.wavelengths,mean - std, mean + std, alpha = 0.4)
    ax.legend()
    plt.pause(0.1)
    while plt.fignum_exists(fig2.number):
        fig2.canvas.flush_events()