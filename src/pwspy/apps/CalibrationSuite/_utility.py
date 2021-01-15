import typing

import cv2
import numpy as np
from skimage.transform import AffineTransform


class CubeSplitter:
    """
    Progressively splits a large cube into smaller and smaller cubes in the xy plane and performs an operation on the smaller cube sections.

    Args:
        arr: The original array we want to work with, May be 2 or 3 dimensional.
    """
    def __init__(self, arr: np.ndarray):
        assert len(arr.shape) in (2, 3), "Only 2 or 3 dimensional arrays are supported."
        self._arr = arr

    def subdivide(self, factor: int) -> np.ndarray:
        """Subdivide the array into a 2d numpy array of sub arrays.

        Args:
            factor: The exponent of 2 that each of the first 2 dimentions of this array should be split by.
            E.G. if `factor` is 3 then the array will be divided into 8 parts on the first to axes resulting in 64 subarrays.
        """
        return self._subdivide(2**factor)

    def _subdivide(self, factor: int) -> np.ndarray:
        """
        Split the array into a 2d numpy array of sub arrays. The remainder pixels that can't be divided up equally are left out.

        Args:
            factor: The number to split each axis of the array by. For example, if `factor` is 2 then the array will be split into 4 arrays with sides that are half as long as the original.

        Returns:
            A 2D numpy array where each element contains a subdivided array from the original array.
        """
        shp = self._arr.shape
        divSize = (shp[0] // factor, shp[1] // factor)
        lst = []
        for i in range(factor):
            subLst = []
            for j in range(factor):
                slc = (slice(divSize[0]*i, divSize[0]*(i+1)), slice(divSize[1]*j, divSize[1]*(j+1)))
                subArr = self._arr[slc]
                subLst.append(subArr)
            lst.append(subLst)
        return np.array(lst)

    def apply(self, func: typing.Callable, factor: int) -> np.ndarray:
        """
        Apply the function `func` to the subarrays.
        Args:
            func: A function that takes a single `numpy.ndarray` as the first argument and returns a single number.
            factor: See the description of the `factor` argument for the `CubeSplitter.subdivide` method.

        Returns:
            A 2d numpy array where the value of each element is the result of `func` for the corresponding subarray.
        """
        medArr = self.subdivide(factor)
        outArr = np.zeros_like(medArr).astype(np.float)
        for i in range(outArr.shape[0]):
            for j in range(outArr.shape[1]):
                outArr[i, j] = func(medArr[i, j])
        return outArr


class DualCubeSplitter:
    def __init__(self, arr1: np.ndarray, arr2: np.ndarray):
        assert arr1.shape == arr2.shape, "Both arrays must have the same shape."
        self._c1 = CubeSplitter(arr1)
        self._c2 = CubeSplitter(arr2)

    def subdivide(self, factor: int):
        return self._c1.subdivide(factor), self._c2.subdivide(factor)

    def apply(self, func, factor: int):
        """
        Apply the function `func` to the subarrays.
        Args:
            func: A function that takes two `numpy.ndarray` as the first two arguments and returns a single number.
            factor: See the description of the `factor` argument for the `CubeSplitter.subdivide` method.

        Returns:
            A 2d numpy array where the value of each element is the result of `func` for the corresponding subarray.
        """
        medArr1, medArr2 = self.subdivide(factor)
        outArr = np.zeros(medArr1.shape[:2])
        for i in range(outArr.shape[0]):
            for j in range(outArr.shape[1]):
                outArr[i, j] = func(medArr1[i, j], medArr2[i, j])
        return outArr


class CVAffineTransform(AffineTransform):
    """
    Extends "SciKit-Image" `AffineTransform` to work more easily with the 2x3 matrices that OpenCV uses as an affine transform.
    """
    @classmethod
    def fromPartialMatrix(cls, matrix: np.ndarray):
        """
        Produces a new instance from a 2x3 matrix of the type used in most OpenCV functions.

        Args:
            matrix: A 2x3 numpy array
        """
        assert matrix.shape == (2, 3)
        matrix = np.vstack([matrix, [0, 0, 1]])
        return AffineTransform(matrix=matrix)

    def toPartialMatrix(self) -> np.ndarray:
        """

        Returns:
            A 2x3 numpy array that can be used with most OpenCV functions.
        """
        return self.params[:2, :]
