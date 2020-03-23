# -*- coding: utf-8 -*-
"""
==================================================
Reflectance Helper (:mod:`pwspy.utility.reflectance.reflectanceHelper`)
==================================================
This module provides a number of functions for calculating simple reflections based on known refractive indices

Functions
----------
.. autosummary::
   :toctree: generated/

   getReflectance
   getRefractiveIndex
"""
__all__ = ['getReflectance', 'getRefractiveIndex']
from numbers import Number

import pandas as pd
import numpy as np
import os
from pwspy.moduleConsts import Material

from .multilayerReflectanceEngine import Stack, Layer, Polarization
from typing import Union, List, Tuple


materialFiles = {
    Material.Glass: 'N-BK7.csv',
    Material.Water: 'Daimon-21.5C.csv',
    Material.Air: 'Ciddor.csv',
    Material.Silicon: 'Silicon.csv',
    Material.Oil_1_7: 'CargilleOil1_7.csv',
    Material.Oil_1_4: "CargilleOil1_4.csv",
    Material.Ipa: 'Sani-DellOro-IPA.csv',
    Material.Ethanol: 'Rheims.csv',
    Material.ITO: 'Konig.csv'}


def __init():
    fileLocation = os.path.join(os.path.split(__file__)[0], 'refractiveIndexFiles')
    ser = {}  # a dictionary of the series by name
    for name, file in materialFiles.items():
        # create a series for each csv file
        arr = np.genfromtxt(os.path.join(fileLocation, file), skip_header=1, delimiter=',')
        _ = pd.DataFrame({'n': arr[:, 1], 'k': arr[:, 2]}, index=arr[:, 0].astype(np.float) * 1e3)
        ser[name] = _

    # Find the first and last indices that won't require us to do any extrapolation
    first = []
    last = []
    for k, v in ser.items():
        first += [v.first_valid_index()]
        last += [v.last_valid_index()]
    first = max(first)
    last = min(last)
    # Interpolate so we don't have any nan values.
    #    df = pd.DataFrame(ser)
    df = pd.concat(ser, axis='columns', keys=materialFiles.keys())
    df = df.interpolate('index')
    return df.loc[first:last]

n = __init()
del __init


def getRefractiveIndex(mat: Material, wavelengths=None) -> pd.Series:
    refractiveIndex = np.array([np.complex(i[0], i[1]) for idx, i in n[mat].iterrows()])
    refractiveIndex = pd.Series(refractiveIndex, n.index)
    if wavelengths is not None: #Need to do interpolation
        wavelengths = pd.Index(wavelengths)
        combinedIdx = refractiveIndex.index.append(
            wavelengths)  # An index that contains all the original index points and all of the new. That way we can interpolate without first throwing away old data.
        from scipy.interpolate import griddata
        out = griddata(refractiveIndex.index, refractiveIndex.values, wavelengths)  #This works with complex numbers
        refractiveIndex = pd.Series(out, index=wavelengths)
    return refractiveIndex


def getReflectance(mat1: Material, mat2: Material, wavelengths: Union[np.ndarray, List, Tuple] = None, NA: float = 0) -> pd.Series:
    """Given the names of two interfaces this provides the reflectance in units of percent.
    If given a series as index the data will be interpolated and reindexed to match the index. If NA is None the result
    is for light with 0 degree angle of incidence. If NA is specified then the result is the disc integral from
    0 to NA, this should match what is seen in the microscope."""
    index = n.index if wavelengths is None else wavelengths
    if isinstance(index, Number):
        index = np.array([index])
    elif not isinstance(index, np.ndarray):
        index = np.array(index)
    s = Stack(wavelengths=index)
    s.addLayer(Layer(mat1, 1e9))  # Add a meter thick layer
    s.addLayer(Layer(mat2, 1e9))
    if NA == 0:
        d = s.calculateReflectance(np.array([0]))
        r = (d[Polarization.TE] + d[Polarization.TM]) / 2
        r = pd.Series(r.squeeze(), index=index)  # Get reflectance at 0 NA (0 incident angle)
    else:
        r = s.circularIntegration(np.linspace(0, NA, num=1000))
    return r
