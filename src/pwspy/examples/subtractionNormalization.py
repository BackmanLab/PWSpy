# -*- coding: utf-8 -*-
"""
Created on Fri Feb  8 14:10:12 2019

@author: Nick Anthony
"""
import numpy as np
from pwspy.dataTypes import ImCube, CameraCorrection
import os.path as osp
from pwspy.utility.reflection import reflectanceHelper
from pwspy.utility.fileIO import loadAndProcess
import typing


def _processIm(q, Iextra, ref, correction: CameraCorrection):
    im = q.get()
    im.correctCameraEffects(correction)

    im = (im - Iextra)
    im.normalizeByReference(ref)
    return im


def subtractionNormalization(rExtra: np.ndarray, rExtraDir: str, ref: ImCube, material: str,
                             correction: CameraCorrection, cubeFiles: typing.List[str]):
    ref.correctCameraEffects(correction)
    ref.filterDust(4)

    theoryR = reflectanceHelper.getReflectance(material, 'glass', index=ref.wavelengths)[np.newaxis, np.newaxis, :]
    I0 = ref.data / (theoryR + rExtra)
    Iextra = rExtra * I0
    ref = (ref - Iextra) / theoryR

    cubes = loadAndProcess(cubeFiles, _processIm, parallel=True, procArgs=[Iextra, ref, correction])

    for c in cubes:
        c.metadata['subtractionCube'] = rExtraDir

    return cubes


if __name__ == '__main__':
    from glob import glob

    rootDir = r'G:\Data\analyzeSystemComparisons\12-5-18 (system comp)\LCPWS\control'
    searchPattern = ['Cell[1-9]', 'Cell10']  # list of search patters
    material = 'ethanol'
    refName = 'Cell998'
    correction = CameraCorrection(2000, (0.977241216, 1.73E-06, 1.70E-11))
    rextraDir = r'G:\Calibrations\4matExtraReflection\LCPWS1\2_5_2019'

    ref = ImCube.loadAny(osp.join(rootDir, refName))
    rextra = np.load(osp.join(rextraDir, 'rextra.npy'))

    files = []
    for patt in searchPattern:
        files.extend(glob(osp.join(rootDir, patt)))

    cubes = subtractionNormalization(rextra, rextraDir, ref, material, correction, files)
