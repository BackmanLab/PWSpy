# -*- coding: utf-8 -*-
"""
Created on Wed Jan  9 15:00:39 2019

@author: Nick Anthony
"""

from pwspy.dataTypes.data import ImCube
import matplotlib.pyplot as plt
import numpy as np

'''
This script Allows the user to select a region of an ImCube. the spectra of this
region is then averaged over the X and Y dimensions. This spectra is then saved
as a reference dataTypes with the same initial dimensions.
Can help to make a reference when you don't actually have one for some reason
'''

if __name__ == '__main__':
    a = ImCube.loadAny(r'G:\Calibrations\CellPhantom\lcpws1\5th\Cell2')

    mask = a.selectLassoROI()
    spec, std = a.getMeanSpectra(mask)
    newData = np.zeros(a.data.shape)
    newData[:, :, :] = spec[np.newaxis, np.newaxis, :]
    ref = ImCube(newData, a.metadata)

    plt.plot(a.wavelengths, spec)
