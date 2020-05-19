# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

# -*- coding: utf-8 -*-
"""
Plots the spectra of the ITO thin film used for calibration.
"""
from pwspy.dataTypes import ImCube, AcqDir
from glob import glob
import matplotlib.pyplot as plt
import numpy as np
import os
from datetime import datetime
from pwspy import dateTimeFormat
import matplotlib as mpl
from pwspy.utility.fileIO import loadAndProcess


def proc(im: ImCube):
    """This function is run in a separate thread/process to load the files."""
    refPath = os.path.join(os.path.split(im.metadata.acquisitionDirectory.filePath)[0], 'Cell999')
    ref = ImCube.fromMetadata(AcqDir(refPath).pws)
    ref.correctCameraEffects()
    im.correctCameraEffects()
    ref.normalizeByExposure()
    im.normalizeByExposure()
    return im, ref

if __name__ == '__main__':
    subDir = r'J:\Calibrations\ITOThinFilm\LCPWS1' # Use '*' to include all subdirectories
    dateStart = '1-16-2020'
    dateEnd = None
    templateName = '1_16_2020'
    
    files = glob(os.path.join(subDir, '*'))
    dates = [os.path.split(f)[-1] for f in files]
    
    
    
    ims = []
    for i in files:
        try:
            ims.append(AcqDir(os.path.join(i, 'Cell1')).pws)
        except:
            print("Skip ", i)
    ims = loadAndProcess(ims, processorFunc=proc)
    
    if dateStart is not None: dateStart = datetime.strptime(dateStart, '%m-%d-%Y')
    else: dateStart = datetime.min
    if dateEnd is not None: dateEnd = datetime.strptime(dateEnd, '%m-%d-%Y')
    else: dateEnd = datetime.max
    
    for i, ref in ims:
        try:
            i.date = datetime.strptime(i.metadata.time, dateTimeFormat)
        except:
            i.date = datetime.strptime(i.metadata.time, dateTimeFormat)
        i.dateString = datetime.strftime(i.date, '%m-%d-%Y')
    
    files = [f for (im, ref), f in zip(ims,files) if dateStart < im.date < dateEnd]
    ims = [(im, ref) for im, ref in ims if dateStart < im.date < dateEnd]
    dates = [datetime.strptime(im.metadata.time, dateTimeFormat) for im, ref in ims]
    dates, ims, files = zip(*sorted(zip(dates, ims, files)))
    
    template = None
    for f, (im, ref) in zip(files,ims):
        if templateName in os.path.split(f):
            print('getting template spectra')
            template = im.getMeanSpectra()[0] / ref.getMeanSpectra()[0]
                
    if template is None:
        print("No template found.")
    
    
    fig, ax = plt.subplots()
    fig.suptitle("Raw Spectrum")
    fig2,ax2 = plt.subplots()
    fig2.suptitle("Mirror Spectrum")
    fig3, ax3 = plt.subplots()
    fig3.suptitle("Normalized Spectrum")
    fig4, ax4 = plt.subplots()
    fig4.suptitle('Template Correlation')
    corrs=[]
    
    colors = mpl.cm.get_cmap('gist_rainbow')(np.linspace(0,1,num=len(files)))
    
    for i, ((im, ref), file) in enumerate(zip(ims, files)):
        #plot spectra
        spectra = im.getMeanSpectra()
        ax.plot(im.wavelengths, spectra[0],label = im.dateString, color = colors[i])
        ax.fill_between(im.wavelengths, spectra[0] + spectra[1], spectra[0] - spectra[1], alpha = 0.4, color = colors[i])
        #Plot mirror spectra
        refSpectra = ref.getMeanSpectra()
        ax2.plot(im.wavelengths, refSpectra[0],label = im.dateString, color = colors[i])
        ax2.fill_between(im.wavelengths, refSpectra[0] + refSpectra[1], refSpectra[0] - refSpectra[1], alpha = 0.4, color = colors[i])
        #plot normalized spectra
        ax3.plot(im.wavelengths, spectra[0] / refSpectra[0],label = im.dateString, color = colors[i])
        std = np.sqrt(spectra[0]**2 / refSpectra[0]**2 * (spectra[1]**2 / spectra[0]**2 + refSpectra[1]**2 / refSpectra[0]**2), )
    #    ax3.fill_between(im.wavelengths,spectra[0] / refSpectra[0] + std, spectra[0] / refSpectra[0] - std, alpha = 0.4, color = colors[i])
        #Calculate correlation
        if template is not None:
            a, b = (spectra[0]/refSpectra[0], template)
            a = (a - np.mean(a)) / (np.std(a) * len(a))
            b = (b - np.mean(b)) / (np.std(b))
            corrs.append(np.correlate(a, b)[0])
    ax.legend()
    ax2.legend()
    ax3.legend()
        
    ax4.bar([i.dateString for i, ref in ims], corrs)
    ax4.set_ylim([.7, 1])
    [tick.set_rotation(45) for tick in ax4.get_xticklabels()]
