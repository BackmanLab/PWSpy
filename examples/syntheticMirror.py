# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 15:44:57 2018

@author: backman05
"""

from pwspython import ImCube
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as sps
import time
import copy

def gaussKernel(radius:int):
    #A kernel that goes to 1 std. It would be better to go out to 2 or 3 std but then you need a larger kernel which greatly increases convolution time.
    lenSide = 1+2*radius
    side = np.linspace(-1,1,num=lenSide)
    X,Y = np.meshgrid(side, side)
    R = np.sqrt(X**2 + Y**2)
    k = np.exp(-(R**2)/2)
    k = k/k.sum() #normalize so the total is 1.
    return k

a = ImCube.fromTiff(r'G:\Vasundhara_MSCs_data\Cell1170')
m = ImCube.fromTiff(r'G:\Vasundhara_MSCs_data\Cell9999')
#(a/m).plotMean() #The mirror is bad so we need to make our own

#print("Select an ROI near the center that doesnt contain cells to get the mirror spectrum")
#mask = (a/m).selectROI()
#spec = a.getMeanSpectra(mask)[0]
#B,A = sps.butter(2, 0.1)
#arr = sps.filtfilt(B,A,a.data, axis=2)#filter along lambda to get rid of sigma
#amp = arr.max(axis=2) #Get the maximum intensity across the field of view.
#kernel = gaussKernel(90)
#print("Start Convolving")
#time.sleep(0.1)
#amp = sps.convolve2d(amp, kernel, mode='same', fillvalue = amp.mean())    #Filter along the field of view to remove the cells.
#print("Done")
#time.sleep(0.1)
#amp = amp / amp.max()   #normalize to one
#mirror = ImCube(spec[np.newaxis,np.newaxis,:] * amp[:,:,np.newaxis], a.metadata)

kernel = gaussKernel(10)
mirror = copy.deepcopy(a) #This doesn't work right. maybe becuaes of the wi
for i in range(a.data.shape[2]):
    print(i)
    time.sleep(0.1)
    mirror.data[:,:,i] = sps.convolve2d(mirror.data[:,:,i],kernel,mode='same',fillvalue=mirror.data[:,:,i].mean())
    
a.plotMean()
mirror.plotMean()
norm = (a/mirror)
norm.plotMean()
plt.figure()
plt.imshow(norm.data.std(axis=2))

