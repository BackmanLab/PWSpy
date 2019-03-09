# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick
"""
import os
import re

import typing
from dataclasses import dataclass
from glob import glob
from typing import List, Tuple

import h5py
import numpy as np
from scipy import io as spio

from pwspy.imCube.ICMetaDataClass import RoiFileFormats


@dataclass(frozen=True)
class CameraCorrection:
    """linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc..."""
    darkCounts: float
    linearityPolynomial: typing.Tuple[float] = None

    def __post_init__(self):
        assert isinstance(self.linearityPolynomial, tuple)


class Roi:
    def __init__(self, name: str, number: int, data: np.ndarray, filePath: str = None, fileFormat: RoiFileFormats=None):
        assert data.dtype == np.bool
        self.data = data
        self.name = name
        self.number = number
        self.filePath = filePath
        self.fileFormat = fileFormat

    @classmethod
    def fromHDF(cls, directory: str, name: str, number: int):
        filePath = os.path.join(directory, f'roi{number}_{name}.h5')
        with h5py.File(filePath) as hf:
            return cls(name, number, hf['data'], filePath=filePath, fileFormat=RoiFileFormats.HDF)

    @classmethod
    def fromMat(cls, directory: str, name: str, number: int):
        filePath = os.path.join(directory, f'BW{number}_{name}.mat')
        return cls(name, number,
                   spio.loadmat(filePath)['BW'].astype(np.bool),
                   filePath=filePath, fileFormat=RoiFileFormats.MAT)

    @classmethod
    def loadAny(cls, directory: str, name: str, number: int):
        try:
            return Roi.fromHDF(directory, name, number)
        except OSError: #For backwards compatibility purposes
            return Roi.fromMat(directory, name, number)

    def toHDF(self, directory):
        savePath = os.path.join(directory, f'roi{self.number}_{self.name}.h5')
        if os.path.exists(savePath):
            raise Exception(f"The Roi file {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            hf.create_dataset('data', data=self.data)

    def deleteFile(self):
        if self.filePath is None:
            raise Exception("There is no filepath variable pointing to a file")
        os.remove(self.filePath)

    @staticmethod
    def getValidRoisInPath(path: str) -> List[Tuple[str, int]]:
        files = glob(path)
        ret = []
        for f in files:
            fname = os.path.split(f)[-1]
            if any([re.match(pattern, fname) is not None for pattern in ["BW.+_.+\\.mat", "roi.+_.+\\.h5"]]):
                ret.append(('_'.join(fname.split('_')[1:]).split('.')[0], int(fname.split('_')[0][2:])))
        return ret