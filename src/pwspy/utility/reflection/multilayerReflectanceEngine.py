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
from enum import Enum, auto

import matplotlib.pyplot as plt
from cycler import cycler
from numbers import Number
from typing import Union, Optional, List
from pwspy.moduleConsts import Material
import pandas as pd
import numpy as np
from pwspy.utility.reflection import reflectanceHelper


class Polarization(Enum):
    TE = auto()  # Transverse Electric Field
    TM = auto()  # Transverse Magnetic Field

class Layer:
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
            n = reflectanceHelper.getRefractiveIndex(self.mat, wavelengths=wavelengths)
            n = pd.Series(n.real, index=n.index)
            return n
        elif isinstance(self.mat, Number):
            return pd.Series(np.array([self.mat]*len(wavelengths)), index=wavelengths)
        elif isinstance(self.mat, pd.Series):
            return self.mat


class Stack:
    def __init__(self, wavelengths: np.ndarray, elements: Optional[List[Layer]] = []):
        assert len(wavelengths.shape) == 1
        self.wavelengths = wavelengths
        self.layers = elements

    def addLayer(self, element: Layer):
        self.layers.append(element)

    def generateMatrix(self) -> np.ndarray:
        """First and last items just have propagation matrices. """
        matrices = []
        lastItem: Layer = None
        for el in self.layers:
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
        for el, col in zip(self.layers, cycle()):
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
        # Actually the order of terms does not appear to matter. This does not account for polarization or incidence angles
        # other than 0 degrees.
        assert len(n1) == len(n2)
        assert np.all(n1.index == n2.index)
        n1 = np.array(n1)
        n2 = np.array(n2)
        matrix = np.array([[n2 + n1, n2 - n1],
                           [n2 - n1, n2 + n1]])
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
        matrix = np.array([[np.exp(-1j * phi), zeroArray],
                           [zeroArray, np.exp(1j * phi)]])
        matrix = np.transpose(matrix, axes=(2, 0, 1))
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

class PolarizedStack(Stack):


    @staticmethod
    def interfaceMatrix(n1: pd.Series, n2: pd.Series, polarization: Polarization, angle: Union[np.ndarray, float], n0: pd.Series) -> np.ndarray:
        #NA = np.sin(angle) * n0 so in theory these variables could both be replaced NA.
        assert len(n1) == len(n2)
        assert np.all(n1.index == n2.index)
        n1 = np.array(n1)
        n2 = np.array(n2)
        theta1 = np.arcsin(n1 * np.sin(angle) / n0)
        theta2 = np.arcsin(n2 * np.sin(theta1) / n1)
        if polarization == Polarization.TE:
            a21 = 1
            N1 = n1 * np.cos(theta1)
            N2 = n2 * np.cos(theta2)
        else:  # Polarization.TM
            a21 = np.cos(theta2) / np.cos(theta1)
            N1 = n1 / np.cos(theta1)
            N2 = n2 / np.cos(theta2)
        matrix = np.array([[N2 + N1, N2 - N1],
                           [N2 - N1, N2 + N1]])
        matrix = np.transpose(matrix, axes=(2, 0, 1))
        matrix = (1 / (2 * a21 * N2))[:, None, None] * matrix
        assert matrix.shape == (len(n1),) + (2, 2)
        return matrix


    @staticmethod
    def propagationMatrix(n: pd.Series, d: float, angle: Union[pd.Series, float],
                          n0: pd.Series) -> np.ndarray:
        # Returns a matrix representing the propagation of light. n should be a pandas Series where the values are complex refractive index
        # and the index fo the Series is the associated wavelengths. with wavelength.
        # for a distance of "d". d and the wavelengths must use the same units.
        wavelengths = n.index
        theta = np.arcsin(n * np.sin(angle) / n0)
        phi = n * d * np.cos(theta) * 2 * np.pi / wavelengths
        # phi = np.array(2 * np.pi * d * n / wavelengths)
        zeroArray = np.zeros(phi.shape)  # Without this our matrix will not shape properly
        matrix = np.array([[np.exp(-1j * phi), zeroArray],
                           [zeroArray, np.exp(1j * phi)]])
        matrix = np.transpose(matrix, axes=(2, 0, 1))
        assert matrix.shape == (len(n),) + (2, 2)
        return matrix

    def generateMatrix(self, polarization: Polarization, angle: float) -> np.ndarray:
        """First and last items just have propagation matrices. """
        matrices = []
        lastItem: Layer = None
        n0 = self.layers[0].getRefractiveIndex(self.wavelengths)
        for el in self.layers:
            if lastItem is not None:
                matrices.append(self.interfaceMatrix(lastItem.getRefractiveIndex(self.wavelengths), el.getRefractiveIndex(self.wavelengths), polarization, angle, n0))
            matrices.append(self.propagationMatrix(el.getRefractiveIndex(self.wavelengths), el.d, angle, n0))
            lastItem = el
        matrices.reverse()

        previousMat = None
        for matrix in matrices:
            if previousMat is not None:
                previousMat = previousMat @ matrix  # Matrix multiplication
            else:
                previousMat = matrix
        return previousMat

    def calculateReflectance(self, angles: List[float]):
        out = {}
        for polarization in Polarization:
            r = []
            for angle in angles:
                print(polarization.name, angle)
                m = self.generateMatrix(polarization, angle)
                assert m.shape == (len(self.wavelengths),) + (2, 2)
                scatterMatrix = np.array([  # A 2x2 scattering matrix. https://en.wikipedia.org/wiki/S-matrix
                    [m[:, 0, 0] * m[:, 1, 1] - m[:, 0, 1] * m[:, 1, 0], m[:, 0, 1]],
                    [-m[:, 1, 0],                              np.ones((m.shape[0],))]])
                scatterMatrix = np.transpose(scatterMatrix, axes=(2, 0, 1))
                scatterMatrix = (1 / m[:, 1, 1])[:, None, None] * scatterMatrix
                R = scatterMatrix[:, 1, 0] * np.conjugate(scatterMatrix[:, 1, 0])  # The reflectance of the stack. This is a real number. Equivalent to np.absolute(scatterMatrix[1, 0]) ** 2
                r.append(np.real(R))
            out[polarization] = np.array(r)
        return out

    def a(self, angles: Union[List[float], np.ndarray]):
        d = self.calculateReflectance(angles)
        # rTM == a**2, rTE == b**2
        rTM = d[Polarization.TM]
        rTE = d[Polarization.TE]
        eccentricity = np.sqrt(1 - rTE / rTM)
        r = (rTM + rTE) / 2
        fig, ax = plt.subplots()
        fig2, ax2 = plt.subplots()
        fig.suptitle("E")
        fig2.suptitle("R")
        ax.set_xlabel("wavelength")
        ax.set_ylabel("Angle")
        ax2.set_xlabel("wavelength")
        ax2.set_ylabel("Angle")
        ax.imshow(eccentricity, extent=[self.wavelengths[0], self.wavelengths[-1], angles[-1], angles[0]], interpolation=None, aspect='auto')
        ax2.imshow(r, extent=[self.wavelengths[0], self.wavelengths[-1], angles[-1], angles[0]], interpolation=None, aspect='auto')
        fig.show()
        fig2.show()
        fig3, ax3 = plt.subplots()
        for i in range(r.shape[0]):
            ax3.plot(r[i, :], label=i)
        ax3.legend()
        # ax3.plot(r.mean(axis=0))
        fig3.show()
        fig4, ax4 = plt.subplots()
        ax4.plot(angles, rTM.mean(axis=1), label='TM')
        ax4.plot(angles, rTE.mean(axis=1), label='TE')
        ax4.plot(angles, r.mean(axis=1), label='R')
        ax4.legend()
        fig4.show()

if __name__ == '__main__':
    num = 30
    wv = np.linspace(500, 700, num=50)
    s = PolarizedStack(wv)
    s.addLayer(Layer(Material.Air, 100000))
    s.addLayer(Layer(Material.Water, 1400))
    s.addLayer(Layer(Material.Glass, 10000))
    # s.addLayer(Layer(Material.Air, 10000))
    s.a(np.linspace(0, np.pi/4, num=num))
    pass
