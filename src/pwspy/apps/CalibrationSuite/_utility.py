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
        assert (len(arr.shape) == 2) or (len(arr.shape) == 3)
        self._arr = arr

    def subdivide(self, factor: int):
        return self._subdivide(2**factor)

    def _subdivide(self, factor: int) -> np.ndarray:
        """
        Split the array into a list of lists of sub arrays. The remainder pixels that can't be divided up equally are left out.

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
