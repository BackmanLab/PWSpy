import typing

import numpy as np


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

    def _subdivide(self, factor: int) -> typing.List[typing.List[np.ndarray]]:
        """
        Split the array into a list of lists of sub arrays. The remainder pixels that can't be divided up equally are left out.

        Args:
            factor: The number to split each axis of the array by. For example, if `factor` is 2 then the array will be split into 4 arrays with sides that are half as long as the original.

        Returns:
            A list of lists of subdivided arrays from the original array.
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