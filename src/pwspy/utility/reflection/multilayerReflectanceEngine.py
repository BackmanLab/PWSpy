'''
Using the wave transfer matrix formalism from chapter 7 of Saleh and Teich
Fundamentals of Photonics, this script calculates the reflectance of a
multilayer dielectric.
http://www.phys.ubbcluj.ro/~emil.vinteler/nanofotonica/TemeControl_FCMD014_Vinteler.pdf
https://en.wikipedia.org/wiki/Transfer-matrix_method_(optics)

m is the final transfer matrix. It should be made by multiplying the matrices
representing each element of the system. If the transmitted light is considered
to be propagating from left to right then the matrices should be in multiplied
in reverse, from right to left.
'''

import matplotlib.pyplot as plt
from cycler import cycler
from numbers import Number
from typing import Union, Optional, List
from pwspy.moduleConsts import Material
import pandas as pd
import numpy as np
from . import reflectanceHelper


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
        n1 = np.array(n1)
        n2 = np.array(n2)
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
        phi = np.array(2 * np.pi * d * n / wavelengths)
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
        scatterMatrix = (1 / m[:, 1, 1])[:, None, None] * scatterMatrix
        R = scatterMatrix[:, 1, 0] * np.conjugate(scatterMatrix[:, 1, 0])  # The reflectance of the stack. This is a real number. Equivalent to np.absolute(scatterMatrix[1, 0]) ** 2
        assert np.max(np.abs(np.imag(R))) == 0
        return np.real(R)
