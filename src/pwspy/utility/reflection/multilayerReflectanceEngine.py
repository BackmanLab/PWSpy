"""
Using the wave transfer matrix formalism from chapter 7 of Saleh and Teich
Fundamentals of Photonics, this script calculates the reflectance of a
multilayer dielectric.
http://www.phys.ubbcluj.ro/~emil.vinteler/nanofotonica/TemeControl_FCMD014_Vinteler.pdf
https://en.wikipedia.org/wiki/Transfer-matrix_method_(optics)

m is the final transfer matrix. It should be made by multiplying the matrices
representing each element of the system. If the transmitted light is considered
to be propagating from left to right then the matrices should be in multiplied
in reverse, from right to left.
"""
from enum import Enum, auto

import matplotlib.pyplot as plt
from cycler import cycler
from numbers import Number
from typing import Union, Optional, List
from pwspy.moduleConsts import Material
import pandas as pd
import numpy as np
import matplotlib as mpl


class Polarization(Enum):
    TE = auto()  # Transverse Electric Field
    TM = auto()  # Transverse Magnetic Field


class Layer:
    """This represents a layer with a thickness and an index of refraction. Note: This whole system only supports
    lossless media, we only use the real part of the index of refraction."""
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
        from .reflectanceHelper import getRefractiveIndex
        if isinstance(self.mat, Material):
            n = getRefractiveIndex(self.mat, wavelengths=wavelengths)
            n = pd.Series(np.real(n), index=n.index)
            return n
        elif isinstance(self.mat, Number):
            return pd.Series(np.array([self.mat]*len(wavelengths)), index=wavelengths)
        elif isinstance(self.mat, pd.Series):
            return self.mat


class StackBase:
    def __init__(self, wavelengths: Union[Number, np.ndarray], elements: Optional[List[Layer]] = None):
        assert len(wavelengths.shape) == 1
        self.wavelengths = wavelengths
        if elements is None:
            self.layers = []
        else:
            self.layers = elements

    def addLayer(self, element: Layer):
        self.layers.append(element)


class NonPolarizedStack(StackBase):
    """Represents a stack of 1d homogenous films. Reflectance can only be calculated at 0 incidence angle in which case
    polarization is irrelevant. This class does not do anything that can't be done with the `Stack`. Indices of refraction must
    be real (no absorption)."""

    def _generateMatrix(self) -> np.ndarray:
        """First and last items just have propagation matrices."""
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
        """Returns a matrix representing the interface between two dielectrics with indices n1 on the left and n2 on the right.
        Actually the order of terms does not appear to matter. This does not account for polarization or incidence angles
        other than 0 degrees."""
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
        """Returns a matrix representing the propagation of light. n should be a pandas Series where the values are
        complex refractive index and the index fo the Series is the associated wavelengths. with wavelength.
        for a distance of `d`. d and the wavelengths must use the same units."""
        wavelengths = n.index
        phi = np.array(2 * np.pi * d * n / wavelengths)
        zeroArray = 0 * phi  # Without this our matrix will not shape properly
        matrix = np.array([[np.exp(-1j * phi), zeroArray],
                           [zeroArray, np.exp(1j * phi)]])
        matrix = np.transpose(matrix, axes=(2, 0, 1))
        assert matrix.shape == (len(n),) + (2, 2)
        return matrix

    def calculateReflectance(self):
        m = self._generateMatrix()
        assert m.shape == (len(self.wavelengths),) + (2, 2)
        scatterMatrix = np.array([ # A 2x2 scattering matrix. https://en.wikipedia.org/wiki/S-matrix
            [m[:, 0, 0] * m[:, 1, 1] - m[:, 0, 1] * m[:, 1, 0], m[:, 0, 1]],
            [-m[:, 1, 0],                              np.ones((m.shape[0],))]])
        scatterMatrix = np.transpose(scatterMatrix, axes=(2, 0, 1))
        scatterMatrix = (1 / m[:, 1, 1])[:, None, None] * scatterMatrix
        R = scatterMatrix[:, 1, 0] * np.conjugate(scatterMatrix[:, 1, 0])  # The reflectance of the stack. This is a real number. Equivalent to np.absolute(scatterMatrix[1, 0]) ** 2
        assert np.max(np.abs(np.imag(R))) == 0
        return np.real(R)


class Stack(StackBase):
    """Represents a stack of 1d homogenous films. Reflectance for the two polarizations can be calculated for a range of
    numerical apertures (angles). Indices of refraction must be real (no absorption)."""
    @staticmethod
    def interfaceMatrix(n1: pd.Series, n2: pd.Series, polarization: Polarization, NAs: np.ndarray) -> np.ndarray:
        """Returns a matrix representing a dieletric interface. n1 and n2 should be a pandas Series where the values are complex refractive index
        and the index of the Series is the associated wavelengths.
        for a distance of "d". d and the wavelengths must use the same units."""
        assert len(n1) == len(n2)
        assert np.all(n1.index == n2.index)
        n1 = n1.values[:, None]
        n2 = n2.values[:, None]
        NAs = NAs[None, :]
        theta1 = np.arcsin(NAs / n1)
        theta2 = np.arcsin(NAs / n2)
        if polarization is Polarization.TE:
            a21 = 1
            N1 = n1 * np.cos(theta1)
            N2 = n2 * np.cos(theta2)
        else:  # Polarization.TM
            a21 = np.cos(theta2) / np.cos(theta1)
            N1 = n1 / np.cos(theta1)
            N2 = n2 / np.cos(theta2)
        matrix = np.array([[N2 + N1, N2 - N1],
                           [N2 - N1, N2 + N1]])
        matrix = np.transpose(matrix, axes=(2, 3, 0, 1))
        matrix = (1 / (2 * a21 * N2))[:, :, None, None] * matrix
        assert matrix.shape == (n1.size, NAs.size) + (2, 2)
        return matrix


    @staticmethod
    def propagationMatrix(n: pd.Series, d: float, NAs: np.ndarray) -> np.ndarray:
        """Returns a matrix representing the propagation of light. n should be a pandas Series where the values are complex refractive index
        and the index fo the Series is the associated wavelengths.
        for a distance of "d". d and the wavelengths must use the same units."""
        wavelengths = np.array(n.index)[:, None]
        n = n.values[:, None]
        NAs = NAs[None, :]
        theta = np.arcsin(NAs / n)
        phi = n * d * np.cos(theta) * 2 * np.pi / wavelengths
        # phi = np.array(2 * np.pi * d * n / wavelengths)
        zeroArray = np.zeros(phi.shape)  # Without this our matrix will not shape properly
        matrix = np.array([[np.exp(-1j * phi), zeroArray],
                           [zeroArray, np.exp(1j * phi)]])
        matrix = np.transpose(matrix, axes=(2, 3, 0, 1)) # Move the angle and wavelength dimensions up front. leave the matrix dimensions as the last two.
        assert matrix.shape == (n.size, NAs.size) + (2, 2)
        return matrix

    def _generateMatrix(self, polarization: Polarization, NAs: np.ndarray) -> np.ndarray:
        """First and last items just have propagation matrices. """
        matrices = []
        lastItem: Layer = None
        for el in self.layers:
            if lastItem is not None:
                matrices.append(self.interfaceMatrix(lastItem.getRefractiveIndex(self.wavelengths), el.getRefractiveIndex(self.wavelengths), polarization, NAs))
            matrices.append(self.propagationMatrix(el.getRefractiveIndex(self.wavelengths), el.d, NAs))
            lastItem = el
        matrices.reverse()

        previousMat = None
        for matrix in matrices:
            if previousMat is not None:
                previousMat = previousMat @ matrix  # Matrix multiplication
            else:
                previousMat = matrix
        return previousMat

    def calculateReflectance(self, NAs: np.ndarray):
        """Given an array of numerical apertures this function returns the reflectance as a dictionary of 2d arrays.
        There is one 2d array for each of the two polarizations. the dimensions of the array is (wavelengths x NAs).
        The total reflectance can be calculated as the average reflectance of the two polarizations. Other ellipsometric
        parameters can also be calculated."""
        out = {}
        for polarization in Polarization:
            m = self._generateMatrix(polarization, NAs)
            scatterMatrix = np.array([  # A 2x2 scattering matrix. https://en.wikipedia.org/wiki/S-matrix
                [m[:, :, 0, 0] * m[:, :, 1, 1] - m[:, :, 0, 1] * m[:, :, 1, 0], m[:, :, 0, 1]],
                [-m[:, :, 1, 0],                              np.ones((m.shape[0], m.shape[1]))]])
            scatterMatrix = np.transpose(scatterMatrix, axes=(2, 3, 0, 1))
            scatterMatrix = (1 / m[:, :, 1, 1])[:, :, None, None] * scatterMatrix
            R = scatterMatrix[:, :, 1, 0] * np.conjugate(scatterMatrix[:, :, 1, 0])  # The reflectance of the stack. This is a real number. Equivalent to np.absolute(scatterMatrix[1, 0]) ** 2
            out[polarization] = R.real
        return out

    def circularIntegration(self, NAs: np.ndarray) -> pd.Series:
        """Given an array of NumericalApertures (usually from 0 to NAMax.) This function integrates the reflectance over
        a disc of Numerical Apertures (Just like in a microscope the Aperture plane is a disc shape, with higher NA
        being further from the center.) Ultimately the result of this integration should match the reflectance measured
        with the same NA."""
        from scipy.integrate import trapz
        d = self.calculateReflectance(NAs)
        r = (d[Polarization.TE] + d[Polarization.TM]) / 2
        r = r * 2 * np.pi * NAs #The aperture plane is a disk, higher NAs have larger circumference disks contributing to them. hence the 2pi*na factor.
        inte = trapz(r, NAs, axis=1)
        int2 = trapz(2 * np.pi * NAs, NAs) #This is used for normalization. basically accounting for the fact that na is proportional to radius in aperture plane, not equal.
        return pd.Series(inte / int2, index=self.wavelengths)

    def plot(self, NAs: np.ndarray, polarization: Polarization = None):
        """Plot various graphs of reflectance vs NA. NAs should be an array of Numerical apertures to have the
        reflectance calculated for. `polarization` can be specified to view the reflectance of only one polarization."""
        d = self.calculateReflectance(nas)
        rTM = d[Polarization.TM]
        rTE = d[Polarization.TE]
        if polarization is None:
            eccentricity = np.sqrt(1 - rTM / rTE)        # rTM == a**2, rTE == b**2
            r = (rTM + rTE) / 2
        elif polarization == Polarization.TE:
            r = rTE
            eccentricity = None
        elif polarization == Polarization.TM:
            r = rTM
            eccentricity = None
        else:
            raise TypeError(f"`polarization` must be Polarization, not {type(polarization)}.")
        fig2, ax2 = plt.subplots()
        fig2.suptitle("R")
        ax2.set_ylabel("wavelength")
        ax2.set_xlabel("NA")
        if eccentricity is not None:
            fig, ax = plt.subplots()
            fig.suptitle("Eccentricity")
            ax.set_ylabel("wavelength")
            ax.set_xlabel("Angle")
            im = ax.imshow(eccentricity, extent=[NAs[0], NAs[-1], self.wavelengths[-1], self.wavelengths[0]], interpolation=None, aspect='auto')
            plt.colorbar(im, ax=ax)
            fig.show()
        im = ax2.imshow(r, extent=[NAs[0], NAs[-1], self.wavelengths[-1], self.wavelengths[0]], interpolation=None, aspect='auto')
        plt.colorbar(im, ax=ax2)
        fig2.show()
        fig3, ax3 = plt.subplots()
        colormap = plt.cm.gist_rainbow
        colors = [colormap(i) for i in np.linspace(0, 0.99, r.shape[1])]
        norm = mpl.colors.Normalize(vmin=NAs[0], vmax=NAs[-1])
        sm = plt.cm.ScalarMappable(cmap=colormap, norm=norm)
        for i in range(r.shape[1]):
            ax3.plot(self.wavelengths, r[:, i], color=colors[i], label=NAs[i])
        plt.colorbar(sm, ax=ax3)
        fig3.show()
        fig4, ax4 = plt.subplots()
        ax4.set_xlabel("NA")
        ax4.plot(NAs, rTM.mean(axis=0), label='TM')
        ax4.plot(NAs, rTE.mean(axis=0), label='TE')
        ax4.plot(NAs, r.mean(axis=0), label='R')
        ax4.legend()
        fig4.show()


if __name__ == '__main__':
    num = 40
    wv = np.linspace(500, 700, num=100)
    s = Stack(wv)
    s.addLayer(Layer(Material.Glass, 100000))
    for i in range(20):
        s.addLayer(Layer(1.2, 650/1.2/4))
        s.addLayer(Layer(1.35, 650/1.35/4))
    # s.addLayer(Layer(Material.ITO, 2000))
    s.addLayer(Layer(Material.Air, 10000))

    nas = np.linspace(0, .2, num=1000)
    s.plot(nas)
    out = s.circularIntegration(nas)
    fig, ax = plt.subplots()
    ax.plot(s.wavelengths, out)
    fig.show()
    pass
