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
"""Provides a number of functions for calculating simple reflections based on known refractive indices

Functions
----------
.. autosummary::
   :toctree: generated/

   getReflectance
   getRefractiveIndex

"""

__all__ = ['getReflectance', 'getRefractiveIndex']

import typing
from numbers import Number

import pandas as pd
import numpy as np
import os
from . import Material

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


def _init():
    """This function initializes data from files when the module is imported."""
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

_n = _init()
del _init


def getRefractiveIndex(mat: Material, wavelengths: typing.Optional[typing.Iterable[float]] =None) -> pd.Series:
    """Get the spectrally dependent refractive index of a material.

    Args:
        mat: The material the retrieve the refractive index of.
        wavelengths: The wavelengths that the refractive index should be calculated at. If left as `None` then the wavelengths
            used will be determined by the original file that the data was pulled from.

    Returns:
        The refractive index. The index of the pandas series is the wavelengths.
    """
    refractiveIndex = np.array([np.complex(i[0], i[1]) for idx, i in _n[mat].iterrows()])
    refractiveIndex = pd.Series(refractiveIndex, _n.index)
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
    If given a series as wavelengths the data will be interpolated and reindexed to match the wavelengths.

    Args:
        mat1: The first material comprising the reflective interface.
        mat2: The second material comprising the reflective interface.
        wavelengths: The wavelengths to calculate the reflectance at.
        NA: The numerical aperture of the system. Reflectance will be calculated by radially integrating results over
            the range of angles present within the numerical aperture. If left as `None` the result is calculated for
            light with a 0 degree angle of incidence.

    Returns:
        The percentage reflectance. The index of the pandas Series is the wavelengths.
    """
    index = _n.index if wavelengths is None else wavelengths
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
