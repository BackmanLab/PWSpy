# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pwspython import ImCube
from glob import glob

def colorbar(mappable):
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    ax = mappable.axes
    fig = ax.figure
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    return fig.colorbar(mappable, cax=cax)

#%%User Input

files = glob('G:/Data/thinfilmcomparison/Cell*')
mfile = r'G:\Data\thinfilmcomparison\Cell997'     #Mirror File

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

print("Select a mirror")
_ = ImCube.loadAny(mfile)
mirror = _.getMeanSpectra(_.selectROI())[0]
#Since our mirror in silicon adjust for the real reflectivity of silicon
mirror = mirror / sref
mirror = np.array(mirror)[np.newaxis,np.newaxis,:]
ims = []
for file in files:
    im = ImCube.loadAny(file)
    ims.append(im)
    #%% Processing
    print("Dividing data by mirror spectra")
    #im._data = np.apply_along_axis(lambda arr: np.divide(arr, mirror),axis=2, arr=im._data)
    im._data = im._data / mirror
    _ = np.array(theory).squeeze()
    ztheory = (_ - _.mean())/(_.std() * _.shape[0])     #Zero normalize for correlation
    zim = (im._data - im._data.mean(axis=2,keepdims = True)) / (im._data.std(axis=2, keepdims = True))  #zero normalize for correlation
    print("Cross correlating with theory")
    corr = np.apply_along_axis(lambda arr: np.correlate(ztheory, arr ,mode = 'same'), axis = 2, arr = zim)
    
    #%% Data Extraction
    print("Extracting data from correlation")
    amp = im._data.max(axis = 2) - im._data.min(axis = 2)   #The amplitude of the spectra.
    corramp = np.max(corr,axis=2)   #The strength of the correlation
    corrmax = np.argmax(corr, axis = 2) - corr.shape[2]//2 #The shift in index that gives the strongest correlation.
    minn = (im._data - np.array(theory).min()).min(axis = 2) #The difference between the minimum of the spectra and the theoretical minima. this indicates unwanted light.
    
    #%% Plotting
    fig,axs = plt.subplots(nrows = 2, ncols=2)
    fig.suptitle()
    imsh = axs[0,0].imshow(amp)
    colorbar(imsh)
    axs[0,0].set_title("Amplitude")
    imsh = axs[0,1].imshow(corrmax, vmin = -5, vmax = 5)
    colorbar(imsh)
    axs[0,1].set_title("Shift (index) to max correlation")
    imsh = axs[1,1].imshow(corramp)
    colorbar(imsh)
    axs[1,1].set_title("Max Correlation")
    imsh = axs[1,0].imshow(minn)
    colorbar(imsh)
    axs[1,0].set_title("Minimum of data")
    
while True:    
    mask = ims[0].selectROI()
    fig2, ax = plt.subplots()
    ax.plot(np.array(theory.index).astype(np.float), np.array(theory["Reflectance"]).astype(np.float), label="Theory")
    for im in ims:
        mean, std = im.getMeanSpectra(mask)
        ax.plot(im.wavelengths,mean, label = "Data")
        ax.fill_between(im.wavelengths,mean - std, mean + std, alpha = 0.4)
    ax.legend()
    plt.pause(0.1)
    while plt.fignum_exists(fig2.number):
        fig2.canvas.flush_events()