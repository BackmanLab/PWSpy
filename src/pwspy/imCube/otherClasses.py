# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick
"""
import json
import os
import re
import cv2

import typing
import dataclasses
from enum import Enum, auto
from glob import glob
from typing import List, Tuple
import matplotlib.pyplot as plt

import h5py
import numpy as np
from scipy import io as spio

class RoiFileFormats(Enum):
    HDF = auto()
    MAT = auto()

@dataclasses.dataclass(frozen=True)
class CameraCorrection:
    """linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc..."""
    darkCounts: float
    linearityPolynomial: typing.Optional[typing.Tuple[float, ...]] = None
    def __post_init__(self):
        #Force the linearity polynomial to be a tuple.
        if self.linearityPolynomial is not None:
            object.__setattr__(self, 'linearityPolynomial', tuple(self.linearityPolynomial))
            assert isinstance(self.linearityPolynomial, tuple)

    def toJsonFile(self, filePath):
        if os.path.splitext(filePath)[-1] != '.json':
            filePath = filePath + '.json'
        with open(filePath, 'w') as f:
            json.dump(dataclasses.asdict(self), f)

    @classmethod
    def fromJsonFile(cls, filePath):
        with open(filePath, 'r') as f:
            return cls(**json.load(f))


class Roi:
    def __init__(self, name: str, number: int, data: np.ndarray, filePath: str = None, fileFormat: RoiFileFormats=None):
        """A class representing a single ROI. consists of a name, a number, and a boolean mask array."""
        assert isinstance(data, np.ndarray), f"data is a {type(data)}"
        assert data.dtype==np.bool
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
            return cls(name, number, np.array(hf[str(number)]).astype(np.bool), filePath=path, fileFormat=RoiFileFormats.HDF)

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
        #TODO why is this so slow
        savePath = os.path.join(directory, f'roi_{self.name}.h5')
        with h5py.File(savePath, 'a') as hf:
            if np.string_(str(self.number)) in hf.keys():
                raise Exception(f"The Roi file {savePath} already contains a dataset {self.number}")
            hf.create_dataset(np.string_(str(self.number)), data=self.data.astype(np.uint8))

    def deleteFile(self):
        if self.filePath is None:
            raise Exception("There is no filepath variable pointing to a file")
        os.remove(self.filePath)

    @staticmethod
    def getValidRoisInPath(path: str) -> List[Tuple[str, int, RoiFileFormats]]:
        patterns = [('BW*_*.mat', RoiFileFormats.MAT), ('roi_*.h5', RoiFileFormats.HDF)]
        files = {fformat: glob(os.path.join(path, p)) for p, fformat in patterns} #Lists of the found files keyed by file format
        ret = []
        for fformat, fileNames in files.items():
            if fformat == RoiFileFormats.HDF:
                for i in fileNames:
                    name = i.split('roi_')[-1][:-3]
                    with h5py.File(i) as hf:
                        for dset in hf.keys():
                            try:
                                ret.append((name, int(dset), RoiFileFormats.HDF))
                            except ValueError:
                                print(f"Warning: File {i} contains uninterpretable dataset named {dset}")
            elif fformat == RoiFileFormats.MAT:
                for i in fileNames: #list in files
                    i = os.path.split(i)[-1]
                    num = int(i.split('_')[0][2:])
                    name = i.split('_')[1][:-4]
                    ret.append((name, num, RoiFileFormats.MAT))
        return ret

    def transform(self, matrix: np.ndarray) -> 'Roi':
        """return a copy of this Roi that has been transformed by an affine transform matrix like the one returned by
        opencv.estimateRigidTransform. This can be obtained using ICBase's getTransform method."""
        out = cv2.warpAffine(self.data.astype(np.uint8), matrix, self.data.shape).astype(np.bool)
        return Roi(self.name, self.number, out)

    def getImage(self, ax: plt.Axes):
        arr = self.data.astype(np.uint8)*255
        arr = np.ma.masked_array(arr, arr==0)
        im = ax.imshow(arr, alpha=0.5, clim=[0, 400], cmap='Reds')
        return im