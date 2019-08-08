# -*- coding: utf-8 -*-
"""
Created on Wed Aug 22 11:05:40 2018

@author: Nick Anthony
"""

import pandas as pd
import numpy as np
import os
from typing import Union, Optional, List
from pwspy.moduleConsts import Material
import matplotlib.pyplot as plt
from cycler import cycler

plt.ion()

materialFiles = {
    Material.Glass: 'N-BK7.csv',
    Material.Water: 'Daimon-21.5C.csv',
    Material.Air: 'Ciddor.csv',
    Material.Silicon: 'Silicon.csv',
    Material.Oil_1_7: 'CargilleOil1_7.csv',
    Material.Oil_1_4: "CargilleOil1_4.csv",
    Material.Ipa: 'Sani-DellOro-IPA.csv',
    Material.Ethanol: 'Rheims.csv'}

def _init():
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
    n = df.loc[first:last]
    return n


n = _init() #initialize the module and delete the initializer function.
del _init


def getReflectance(mat1: Material, mat2: Material, index=None) -> pd.Series:
    """Given the names of two interfaces this provides the reflectance in units of percent.
    If given a series as index the data will be interpolated and reindexed to match the index."""

    nc1 = np.array([np.complex(i[0], i[1]) for idx, i in n[mat1].iterrows()])  # complex index for material 1
    nc2 = np.array([np.complex(i[0], i[1]) for idx, i in n[mat2].iterrows()])
    result = np.abs(((nc1 - nc2) / (nc1 + nc2)) ** 2)
    result = pd.Series(result, index=n.index)
    if index is not None:
        index = pd.Index(index)
        combinedIdx = result.index.append(
            index)  # An index that contains all the original index points and all of the new. That way we can interpolate without first throwing away old data.
        result = result.reindex(combinedIdx)
        result = result.sort_index()
        result = result.interpolate()
        result = result[~result.index.duplicated()]  # remove duplicate indices to avoid error
        result = result.reindex(index)  # reindex again to get rid of unwanted index points.
    return result


# -*- coding: utf-8 -*-
"""
Created on Fri Jan 29 12:11:42 2016
@author: nick anthony
"""

from mpl_toolkits.mplot3d import Axes3D

'''
Using the wave transfer matrix formalism form chapter 7 of Saleh and Teich
Fundamentals of Photonics, this script calculates the reflectance of a
multilayer dielectric.
'''
class Element:
    def __init__(self, n: Union[float, np.ndarray], d: float, name: str = ''):
        self.n = n
        self.d = d
        self.name = name


#TODO support 5d arrays where 2 dimensions are matrix mult dimensions and the other two dimensions are angle and lambda and index.
class Stack:
    def __init__(self, elements: Optional[List[Element]] = []):
        self._elements = elements

    def addElement(self, element: Element):
        self._elements.append(element)

    def generateMatrix(self) -> np.ndarray:
        """First and last items just have propagation matrices. """
        matrices = []
        lastItem: Element = None
        for el in self._elements:
            if lastItem is not None:
                matrices.append(interface(lastItem.n, el.n))
            matrices.append(propagation(lamb, el.n, el.d))
        matrices.reverse()

        previousMat = None
        for matrix in matrices:
            if previousMat is not None:
                previousMat = np.matmul(previousMat, matrix)
        return previousMat

    def plot(self):
        cycle = cycler('color', ['r', 'g', 'b', 'y', 'c', 'm'])
        fig, ax = plt.subplots()
        ax.set_prop_cycle(cycle)
        startCoord = 0
        for el, col in zip(self._elements, cycle()):
            r = plt.Rectangle((startCoord, 0), el.d, 1, color=col['color'])
            t = plt.Text(r.xy[0]+r.get_width()/2, .5, f"{el.name}: {np.mean(el.n)}")
            startCoord = startCoord + el.d
            ax.add_patch(r)
            ax.add_artist(t)
        ax.set_xlim([0, startCoord])
        plt.show()
        while True:
            plt.pause(.1)
if __name__ == '__main__':
    s = Stack()
    s.addElement(Element(3, 5, 'rar'))
    s.addElement(Element(.2, .4, 'aa'))
    s.plot()

def interface(n1, n2):
    # Returns a matrix representing the interface between two dielectrics with indices n1 on the left and n2 on the right.
    # Actually the order of terms does not appear to matter.
    return 1 / (2 * n2) * np.matrix([[n2 + n1, n2 - n1], [n2 - n1, n2 + n1]])


def propagation(lamb: float, n: Union[np.ndarray, float], d: float):
    # Returns a matrix representing the propagation of light with wavelength, "lamb", through homogenous material wth index, "n",
    # for a distance of "d". d and lamb must use the same units.
    phi = n * 2 * np.pi / lamb * d
    return np.matrix([[np.exp(-phi * 1j), 0], [0, np.exp(1j * phi)]])


def calc(m):
    # calculates reflected power given a transfer matrix, "m".
    def m_to_scatter(m):
        return (1 / m[1, 1]) * np.array([[m[0, 0] * m[1, 1] - m[0, 1] * m[1, 0], m[0, 1]], [-m[1, 0], 1]])

    scatter = m_to_scatter(m)
    Reflect = np.real(scatter[1, 0] * np.conj(scatter[1, 0]))
    return Reflect


'''
m is the final transfer matrix. It should be made by multiplying the matrices
representing each element of the system. If the transmitted light is considered
to be propagating from left to right then the matrices should be in multiplied
in reverse, from right to left.
'''

param = np.array([1, 2, 3, 10])

R = np.zeros((5000, len(param)))
High_lambda = 12000
Low_lambda = 500
lp = 7.5e3
lb = lp * 3 / 2

for l in np.linspace(Low_lambda, High_lambda, num=R.shape[0]):
    print('%d' % ((l - Low_lambda) / (High_lambda - Low_lambda) * 100) + '%')

    for p in param:
        n3 = 1
        n2 = n3 + p
        '''
        Here is the series of multiplied matrices
        '''
        m = (propagation(l, n3, lb / (4 * n3)) * interface(n3, n2) * propagation(l, n2, lb / (4 * n2)) * interface(n2, n3)) ** 10

        R[np.where(np.linspace(Low_lambda, High_lambda, num=R.shape[0]) == l)[0][0], np.where(param == p)[0][0]] = (calc(m))
hf = plt.figure()
ha = hf.add_subplot(111, projection='3d')
X, Y = np.meshgrid(param, np.linspace(Low_lambda, High_lambda, num=R.shape[0]))
ha.plot_surface(X, Y, R, cstride=1, rstride=10)
ha.set_ylabel('Wavelength (nm)')
ha.set_xlabel('Parameter')
ha.set_zlabel('Reflectance')
plt.figure()
plt.xlabel('Wavelength (nm)')
plt.ylabel('Reflectance')
for i in range(R.shape[1]):
    plt.plot(np.linspace(Low_lambda, High_lambda, num=R.shape[0]), R[:, i], label=str(param[i]))
plt.legend()
plt.show()
