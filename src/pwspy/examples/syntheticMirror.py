# -*- coding: utf-8 -*-
"""
Created on Fri Dec  7 15:44:57 2018

@author: Nick Anthony
"""

import copy

import matplotlib.pyplot as plt
from pwspy.dataTypes import ImCube

'''
This script blurs an image cube in the xy direction. Allows you to turn an
image of cells into something that can be used as a reference image, assuming
most of the the FOV is glass.
'''
if __name__ == '__main__':
    a = ImCube.fromTiff(r'G:\Vasundhara_MSCs_data\Cell1170')

    mirror = copy.deepcopy(a)  # This doesn't work right. maybe becuaes of the wi
    mirror.filterDust(10)

    a.plotMean()
    mirror.plotMean()
    norm = (a / mirror)
    norm.plotMean()
    plt.figure()
    plt.imshow(norm.data.std(axis=2))
