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

'''
This script blurs an image cube in the xy direction. Allows you to turn an
image of cells into something that can be used as a reference image, assuming
most of the the FOV is glass.
'''


a = ImCube.fromTiff(r'G:\Vasundhara_MSCs_data\Cell1170')


mirror = copy.deepcopy(a) #This doesn't work right. maybe becuaes of the wi
mirror.filterDust(10)

a.plotMean()
mirror.plotMean()
norm = (a/mirror)
norm.plotMean()
plt.figure()
plt.imshow(norm.data.std(axis=2))

