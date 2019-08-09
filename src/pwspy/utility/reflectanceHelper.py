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
from numbers import Number

class ReflectanceHelper:
    materialFiles = {
        Material.Glass: 'N-BK7.csv',
        Material.Water: 'Daimon-21.5C.csv',
        Material.Air: 'Ciddor.csv',
        Material.Silicon: 'Silicon.csv',
        Material.Oil_1_7: 'CargilleOil1_7.csv',
        Material.Oil_1_4: "CargilleOil1_4.csv",
        Material.Ipa: 'Sani-DellOro-IPA.csv',
        Material.Ethanol: 'Rheims.csv'}

    _instance = None

    @staticmethod
    def getInstance():
        """ Static access method. """
        if ReflectanceHelper._instance is None:
            ReflectanceHelper()
        return ReflectanceHelper._instance

    def __init__(self):
        """ Virtually private constructor. """
        if ReflectanceHelper._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            ReflectanceHelper._instance = self
        fileLocation = os.path.join(os.path.split(__file__)[0], 'refractiveIndexFiles')
        ser = {}  # a dictionary of the series by name
        for name, file in self.materialFiles.items():
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
        df = pd.concat(ser, axis='columns', keys=self.materialFiles.keys())
        df = df.interpolate('index')
        self.n = df.loc[first:last]


    def getReflectance(self, mat1: Material, mat2: Material, wavelengths=None) -> pd.Series:
        """Given the names of two interfaces this provides the reflectance in units of percent.
        If given a series as index the data will be interpolated and reindexed to match the index."""

        # nc1 = np.array([np.complex(i[0], i[1]) for idx, i in n[mat1].iterrows()])  # complex index for material 1
        # nc2 = np.array([np.complex(i[0], i[1]) for idx, i in n[mat2].iterrows()])
        nc1 = self.getRefractiveIndex(mat1)
        nc2 = self.getRefractiveIndex(mat2)
        result = np.abs(((nc1 - nc2) / (nc1 + nc2)) ** 2)
        result = pd.Series(result, index=self.n.index)
        if wavelengths is not None:
            wavelengths = pd.Index(wavelengths)
            combinedIdx = result.index.append(
                wavelengths)  # An index that contains all the original index points and all of the new. That way we can interpolate without first throwing away old data.
            result = result.reindex(combinedIdx)
            result = result.sort_index()
            result = result.interpolate(method='index')  #Use the values of the index rather than assuming it is linearly spaced.
            result = result[~result.index.duplicated()]  # remove duplicate indices to avoid error
            result = result.reindex(wavelengths)  # reindex again to get rid of unwanted index points.
        return result


    def getRefractiveIndex(self, mat: Material, wavelengths=None) -> pd.Series:
        refractiveIndex = np.array([np.complex(i[0], i[1]) for idx, i in self.n[mat].iterrows()])
        refractiveIndex = pd.Series(refractiveIndex, self.n.index)
        if wavelengths is not None: #Need to do interpolation
            wavelengths = pd.Index(wavelengths)
            combinedIdx = refractiveIndex.index.append(
                wavelengths)  # An index that contains all the original index points and all of the new. That way we can interpolate without first throwing away old data.
            from scipy.interpolate import griddata
            out = griddata(refractiveIndex.index, refractiveIndex.values, wavelengths)  #This works with complex numbers
            refractiveIndex = pd.Series(out, index=wavelengths)
        return refractiveIndex

reflectanceHelper = ReflectanceHelper.getInstance()

'''
Using the wave transfer matrix formalism from chapter 7 of Saleh and Teich
Fundamentals of Photonics, this script calculates the reflectance of a
multilayer dielectric.
http://www.phys.ubbcluj.ro/~emil.vinteler/nanofotonica/TemeControl_FCMD014_Vinteler.pdf
https://en.wikipedia.org/wiki/Transfer-matrix_method_(optics)
'''
class Element:
    def __init__(self, mat: Union[Number, pd.Series, Material], d: float, name: str = None):
        if not isinstance(mat, (Number, pd.Series, Material)):
            raise TypeError(f"Type {type(mat)} is not supported")
        self.mat = mat
        self.d = d
        if name is None and isinstance(mat, Material):
            self.name = mat.name
        else:
            self.name = name

    def getRefractiveIndex(self, wavelengths: np.ndarray) -> pd.Series:
        if isinstance(self.mat, Material):
            return reflectanceHelper.getRefractiveIndex(self.mat, wavelengths=wavelengths)
        elif isinstance(self.mat, Number):
            return pd.Series(np.array([self.mat]*len(wavelengths)), index=wavelengths)
        elif isinstance(self.mat, pd.Series):
            return self.mat


#TODO support 5d arrays where 2 dimensions are matrix mult dimensions and the other two dimensions are angle and lambda and index.
class Stack:
    def __init__(self, wavelengths: np.ndarray, elements: Optional[List[Element]] = []):
        assert len(wavelengths.shape) == 1
        self.wavelengths = wavelengths
        self.elements = elements

    def addElement(self, element: Element):
        self.elements.append(element)

    def generateMatrix(self) -> np.ndarray:
        """First and last items just have propagation matrices. """
        matrices = []
        lastItem: Element = None
        for el in self.elements:
            if lastItem is not None:
                matrices.append(self.interfaceMatrix(lastItem.getRefractiveIndex(self.wavelengths), el.getRefractiveIndex(self.wavelengths)))
            matrices.append(self.propagationMatrix(el.getRefractiveIndex(self.wavelengths), el.d))
            lastItem = el
        matrices.reverse()

        previousMat = None
        for matrix in matrices:
            if previousMat is not None:
                previousMat = previousMat @ matrix  # Matrix multiplication
            else:
                previousMat = matrix
        return previousMat

    def plot(self):
        cycle = cycler('color', ['r', 'g', 'b', 'y', 'c', 'm'])
        fig, ax = plt.subplots()
        ax.set_prop_cycle(cycle)
        startCoord = 0
        for el, col in zip(self.elements, cycle()):
            r = plt.Rectangle((startCoord, 0), el.d, 1, color=col['color'])
            t = plt.Text(r.xy[0]+r.get_width()/2, .5, f"{el.name}: {np.mean(el.getRefractiveIndex(self.wavelengths))}")
            startCoord = startCoord + el.d
            ax.add_patch(r)
            ax.add_artist(t)
        ax.set_xlim([0, startCoord])
        plt.show()


    @staticmethod
    def interfaceMatrix(n1: pd.Series, n2: pd.Series) -> np.ndarray:
        # Returns a matrix representing the interface between two dielectrics with indices n1 on the left and n2 on the right.
        # Actually the order of terms does not appear to matter.
        assert len(n1) == len(n2)
        assert np.all(n1.index == n2.index)
        matrix = np.array([[n2 + n1, n2 - n1], [n2 - n1, n2 + n1]])
        matrix = np.transpose(matrix, axes=(2, 0, 1))
        matrix = (1 / (2 * n2))[:, None, None] * matrix
        assert matrix.shape == (len(n1),) + (2, 2)
        return matrix

    @staticmethod
    def propagationMatrix(n: pd.Series, d: float) -> np.ndarray:
        # Returns a matrix representing the propagation of light. n should be a pandas Series where the values are complex refractive index
        # and the index fo the Series is the associated wavelengths. with wavelength.
        # for a distance of "d". d and the wavelengths must use the same units.
        wavelengths = n.index
        phi = (2 * np.pi / d) * (n / wavelengths)
        zeroArray = 0 * phi  # Without this our matrix will not shape properly
        matrix = np.array([[np.exp(-phi * 1j), zeroArray], [zeroArray, np.exp(1j * phi)]])
        matrix = np.transpose(matrix, axes=(2,0,1))
        assert matrix.shape == (len(n),) + (2, 2)
        return matrix

    def calculateReflectance(self):
        m = self.generateMatrix()
        assert m.shape == (len(self.wavelengths),) + (2, 2) #TODO for now this is how it works. should be expanded to higher dimensionality later.
        scatterMatrix = np.array([ # A 2x2 scattering matrix. https://en.wikipedia.org/wiki/S-matrix
            [m[:, 0, 0] * m[:, 1, 1] - m[:, 0, 1] * m[:, 1, 0], m[:, 0, 1]],
            [-m[:, 1, 0],                              np.ones((m.shape[0],))]])
        scatterMatrix = np.transpose(scatterMatrix, axes=(2, 0, 1))
        R = scatterMatrix[:, 1, 0] * np.conjugate(scatterMatrix[:, 1, 0])  # The reflectance of the stack. This is a real number. Equivalent to np.absolute(scatterMatrix[1, 0]) ** 2
        assert np.max(np.abs(np.imag(R))) == 0
        return np.real(R)


if __name__ == '__main__':
    wv = np.linspace(500,750)
    s = Stack(wv)
    s.addElement(Element(Material.Air, 5000, 'rar'))
    s.addElement(Element(Material.Glass, 20000, 'aa'))
    # s.addElement(Element(Material.Air, 5000, 'out'))
    r=s.calculateReflectance()
    # s.plot()
    plt.figure()
    plt.plot(s.wavelengths, r)
    plt.plot(reflectanceHelper.getReflectance(Material.Air, Material.Water, wavelengths=wv))
    plt.show()
    b = 3




'''
m is the final transfer matrix. It should be made by multiplying the matrices
representing each element of the system. If the transmitted light is considered
to be propagating from left to right then the matrices should be in multiplied
in reverse, from right to left.
'''

# param = np.array([1, 2, 3, 10])
#
# R = np.zeros((5000, len(param)))
# High_lambda = 12000
# Low_lambda = 500
# lp = 7.5e3
# lb = lp * 3 / 2
#
# for l in np.linspace(Low_lambda, High_lambda, num=R.shape[0]):
#     print('%d' % ((l - Low_lambda) / (High_lambda - Low_lambda) * 100) + '%')
#
#     for p in param:
#         n3 = 1
#         n2 = n3 + p
#         '''
#         Here is the series of multiplied matrices
#         '''
#         m = (propagation(l, n3, lb / (4 * n3)) * interface(n3, n2) * propagation(l, n2, lb / (4 * n2)) * interface(n2, n3)) ** 10
#
#         R[np.where(np.linspace(Low_lambda, High_lambda, num=R.shape[0]) == l)[0][0], np.where(param == p)[0][0]] = (calc(m))
# hf = plt.figure()
# ha = hf.add_subplot(111, projection='3d')
# X, Y = np.meshgrid(param, np.linspace(Low_lambda, High_lambda, num=R.shape[0]))
# ha.plot_surface(X, Y, R, cstride=1, rstride=10)
# ha.set_ylabel('Wavelength (nm)')
# ha.set_xlabel('Parameter')
# ha.set_zlabel('Reflectance')
# plt.figure()
# plt.xlabel('Wavelength (nm)')
# plt.ylabel('Reflectance')
# for i in range(R.shape[1]):
#     plt.plot(np.linspace(Low_lambda, High_lambda, num=R.shape[0]), R[:, i], label=str(param[i]))
# plt.legend()
# plt.show()
