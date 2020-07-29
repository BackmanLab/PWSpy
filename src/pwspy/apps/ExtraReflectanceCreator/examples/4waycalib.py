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
Created on Tue Nov 20 13:13:34 2018

@author: Nick Anthony

This functionality has now been replaced in the ERCreator application. This is just an example script.
This script is now outdated and will not work. See the `generateExtraReflectance` example for a more up to date example.
"""


from pwspy.dataTypes import CameraCorrection
from pwspy.utility.fileIO import loadAndProcess
from pwspy.utility.reflection import reflectanceHelper, Material
import pwspy.utility.reflection.extraReflectance as er
from glob import glob
import matplotlib.pyplot as plt
import os
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
import random


def processIm(im):
    im.correctCameraEffects(CameraCorrection(100))
#    im.subtractDarkCounts(2000)
#    im.data = np.polynomial.polynomial.polyval(im.data, [0, 0.977241216, 1.73E-06, 1.70E-11]) #LCPWS 1 linearization
    im.normalizeByExposure()
    im.filterDust(6)
    return im


if __name__ == '__main__':
    __spec__ = None
    plt.interactive(True)
    
    exclude = [(Material.Water, Material.Ipa), (Material.Water, Material.Ethanol)]
    rootDir = r'/home/nick/Desktop/4matExtraReflection/LCPWS1/1_23_2019'
    produceRextraCube = True
    plotResults = True
    
    materials = [('air', Material.Air), ('water', Material.Water), ('ipa', Material.Ipa), ('ethanol', Material.Ethanol)]
    
    fig, axes = plt.subplots(ncols=2)
    axes[0].set_ylabel('n')
    axes[0].set_xlabel('nm')
    axes[0].set_title("Index of Refraction")
    axes[1].set_ylabel('reflectance')
    axes[1].set_xlabel('nm')
    axes[1].set_title("Glass Interface Reflectance")
    [axes[0].plot(reflectanceHelper.getRefractiveIndex(mat), label=matName) for matName, mat in materials]
    axes[0].legend()
    [axes[1].plot(reflectanceHelper.getReflectance(mat, Material.Glass).index, reflectanceHelper.getReflectance(mat, Material.Glass), label=matName) for matName, mat in materials]
    axes[1].legend()
    
    fileFrame = pd.DataFrame([{'setting': 'none', 'material': m, 'cube': cube} for m in materials for cube in glob(os.path.join(rootDir, m, 'Cell*'))])
    cubes = loadAndProcess(fileFrame, processIm, parallel=True)

    theoryR = er.getTheoreticalReflectances(list(zip(*materials))[1], cubes['cube'][0].wavelengths, 0.52)
    matCombos = er.generateMaterialCombos(list(zip(*materials))[1], excludedCombos=exclude)
    if plotResults:
        mask = random.choice(cubes['cube']).selectLassoRoi()
        er.plotExtraReflection(cubes, theoryR, matCombos, 0.52, mask, plotReflectionImages=False)
        with PdfPages(os.path.join(rootDir, "figs.pdf")) as pp:
            for i in plt.get_fignums():
                f = plt.figure(i)
                f.set_size_inches(9, 9)
                pp.savefig(f)
    if produceRextraCube:
        for sett in set(cubes['setting']):
            allCombos = er.getAllCubeCombos(matCombos, cubes[cubes['setting'] == sett])
            erCube, rextras, plots = er.generateRExtraCubes(allCombos, theoryR, 0.52)
            erCube.toHdfFile(rootDir, f'rextra_{sett}')
