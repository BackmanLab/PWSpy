# -*- coding: utf-8 -*-
"""
Created on Wed Jan 13 11:45:44 2021

@author: backman05
"""

import pwspy.dataTypes as pwsdt
from pwspy.utility.plotting import PlotNd

imageDirectory = r'\\backmanlabnas.myqnapcloud.com\home\Year3\ethanolTimeSeries\LTL20l_Pure\Track_3hrs\Cell3'

acquisition = pwsdt.AcqDir(imageDirectory)

roiSpecs = acquisition.getRois()
print("ROIs:\n", roiSpecs)

imCube = acquisition.pws.toDataClass()
kCube = pwsdt.KCube.fromImCube(imCube)
del imCube

opd, opdValues = kCube.getOpd(isHannWindow = False, indexOpdStop = 50)

ri = 1.37
opdValues = opdValues / (2 * ri)

plotWindow = PlotNd(opd, names=('y', 'x', 'depth'),
                    indices=(None, None, opdValues), title="Estimated Depth")