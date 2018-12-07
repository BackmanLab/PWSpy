# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 15:44:57 2018

@author: backman05
"""

from pwspython import ImCube
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as sps

def gaussKernel(radius:int):
    lenSide = 1+2*radius
    X,Y = np.meshgrid(np.linspace(-3,3,num=lenSide), np.linspace(-3,3,num=lenSide))
    R = np.sqrt(X**2 + Y**2)
    k = np.exp(-(R**2)/2)
    k = k/k.sum() #normalize so the total is 1.
    return k

a = ImCube.fromTiff(r'G:\Vasundhara_MSCs_data\Cell1170')
m = ImCube.fromTiff(r'G:\Vasundhara_MSCs_data\Cell9999')
#(a/m).plotMean() #The mirror is bad so we need to make our own

print("Select an ROI near the center that doesnt contain cells to get the mirror spectrum")
mask = (a/m).selectROI()
spec = a.getMeanSpectra(mask)[0]

B,A = sps.butter(2, 0.1)
arr = sps.filtfilt(B,A,a.data, axis=2)#filter along lambda to get rid of sigma
amp = arr.max(axis=2) #Get the maximum intensity across the field of view.
kernel = gaussKernel(200)
print("Start Convolving")
amp = sps.convolve2d(amp, kernel, mode='same', fillvalue = amp.mean())    #Filter along the field of view to remove the cells.
print("Done")
amp = amp / amp.max()   #normalize to one


mirror = ImCube(spec[np.newaxis,np.newaxis,:] * amp[:,:,np.newaxis], a.metadata)
a.plotMean()
mirror.plotMean()
(a/mirror).plotMean()
