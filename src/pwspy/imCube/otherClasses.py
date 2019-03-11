# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick
"""
import os
import re

import typing
from dataclasses import dataclass
from enum import Enum, auto
from glob import glob
from typing import List, Tuple

import h5py
import numpy as np
from scipy import io as spio

class RoiFileFormats(Enum):
    HDF = auto()
    MAT = auto()

@dataclass(frozen=True)
class CameraCorrection:
    """linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc..."""
    darkCounts: float
    linearityPolynomial: typing.Tuple[float, ...] = None

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
        path = os.path.join(directory, f'roi_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            return cls(name, number, hf[number], filePath=path, fileFormat=RoiFileFormats.HDF)

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
        savePath = os.path.join(directory, f'roi_{self.name}.h5')
        with h5py.File(savePath, 'w') as hf:
            if self.number in hf.keys():
                raise Exception(f"The Roi file {savePath} already exists.")
            hf.create_dataset(self.number, data=self.data, compression=3)

    def deleteFile(self):
        if self.filePath is None:
            raise Exception("There is no filepath variable pointing to a file")
        os.remove(self.filePath)

    @staticmethod
    def getValidRoisInPath(path: str) -> List[Tuple[str, int, RoiFileFormats]]:
        patterns = [('BW*_*.mat', RoiFileFormats.MAT), ('*_roi.h5', RoiFileFormats.HDF)]
        files = {format: glob(os.path.join(path, p)) for p, format in patterns}
        ret = []
        for k, v in files.items():
            if k == RoiFileFormats.HDF:
                for i in v:
                    raise NotImplementedError
            elif k == RoiFileFormats.MAT:
                for i in v: #list in files
                    i = os.path.split(i)[-1]
                    num = int(i.split('_')[0][2:])
                    name = i.split('_')[1][:-4]
                    ret.append((name, num, RoiFileFormats.MAT))
        return ret


