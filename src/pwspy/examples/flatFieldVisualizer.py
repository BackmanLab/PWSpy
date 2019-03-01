# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pwspy import ImCube, reflectanceHelper
from glob import glob
import os
from pwspy.utility import loadAndProcess

plt.ion()

__spec__ = None
def colorbar(mappable):
    from mpl_toolkits.axes_grid1 import make_axes_locatable
    ax = mappable.axes
    fig = ax.figure
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="5%", pad=0.05)
    return fig.colorbar(mappable, cax=cax)

def proc(q ,mmask, sref, theory):
    im = q.get()
#    im.subtractDarkCounts(1957)
    print("Dividing data by mirror spectra")
    mirror = im.getMeanSpectra(mmask)[0][np.newaxis,np.newaxis,:]
    im.data = im.data / (mirror / np.array(sref).squeeze())
    _ = np.array(theory).squeeze()
    ztheory = (_ - _.mean())/(_.std() * _.shape[0])     #Zero normalize for correlation
    zim = (im.data - im.data.mean(axis=2,keepdims = True)) / (im.data.std(axis=2, keepdims = True))  #zero normalize for correlation
    print("Cross correlating with theory")
    corr = np.apply_along_axis(lambda arr: np.correlate(ztheory, arr ,mode = 'same'), axis = 2, arr = zim)
    
    # Data Extraction
    print("Extracting data from correlation")
    amp = im.data.max(axis = 2) - im.data.min(axis = 2)   #The amplitude of the spectra.
    corramp = np.max(corr,axis=2)   #The strength of the correlation
    corrmax = np.argmax(corr, axis = 2) - corr.shape[2]//2 #The shift in index that gives the strongest correlation.
    minn = (im.data.min(axis=2) - np.array(theory).min()) #The difference between the minimum of the spectra and the theoretical minima. this indicates unwanted light.

    return im, amp, corramp, corrmax, minn

if __name__ == "__main__":
    #%%User Input
    fileNameTranslator = {'aclosefopen':"Aperture Closed",'alclosefopen':"Aperture Barely Open",'aopenfopen':"Aperture Open", 'alopenfopen':"Aperture Barely Closed"}
    files = glob('G:/Data/thinfilmcomparisonround2/a*')
    files = [i for i in files if ('fmid' not in i) and ("fclose" not in i)]
    #%% Loading
    theory = pd.read_csv(os.path.join(os.path.split(__file__)[0], 'thinFilmData', 'Reflectance-calcs.txt'), delimiter = '\t', index_col = 0)   #The theoretical reflectance for a 1um thin film. silica on silicon.
    theory = theory.loc[500:700:2]
    theory = theory * 100
    sref = reflectanceHelper.getReflectance('air','silicon', index = range(500,701,2))
    
    print("Select a mirror")
    mmask = ImCube.loadAny(files[0]).selectROI()
    #%% Processing
    result = loadAndProcess(files, processorFunc=proc, specifierNames=['filename'], parallel = True, procArgs = (mmask, sref, theory))
    
    ims = [res[0] for res in result]
    for im, amp, corramp, corrmax, minn in result:   
        # Plotting
        fig,axs = plt.subplots(nrows = 2, ncols=2)
        fig.suptitle(im.filename)
        imsh = axs[0,0].imshow(amp, vmin = np.percentile(amp,1), vmax = np.percentile(amp,99))
        colorbar(imsh)
        axs[0,0].set_title("Amplitude")
        imsh = axs[0,1].imshow(corrmax, vmin = -5, vmax = 5)
        colorbar(imsh)
        axs[0,1].set_title("Shift (index) to max correlation")
        imsh = axs[1,1].imshow(corramp, vmin = 0, vmax = 1)
        colorbar(imsh)
        axs[1,1].set_title("Max Correlation")
        imsh = axs[1,0].imshow(minn, vmin = np.percentile(minn,1), vmax=np.percentile(minn,1))
        colorbar(imsh)
        axs[1,0].set_title("Minimum of data")
        for ax in axs.flatten():
            ax.axis('off')

    while True:    
        try:
            mask = ims[0].selectROI()
            fig2, ax = plt.subplots()
            ax.plot(np.array(theory.index).astype(np.float), np.array(theory["Reflectance"]).astype(np.float), label="Theory")
            for im in ims:
                mean, std = im.getMeanSpectra(mask)
                ax.plot(im.wavelengths,mean, label = fileNameTranslator[im.filename])
                ax.fill_between(im.wavelengths,mean - std, mean + std, alpha = 0.4)
            ax.legend()
            ax.set_xlabel("Wavelength (nm)")
            ax.set_ylabel("Reflectance")
            fig2.suptitle("Thin Film Comparison")
            plt.pause(0.1)
            while plt.fignum_exists(fig2.number):
                fig2.canvas.flush_events()
        except Exception as e:
            print(e)