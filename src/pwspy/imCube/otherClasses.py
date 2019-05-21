# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick
"""
from __future__ import annotations
import json
import os
import re
from matplotlib import patches, path
import typing
import dataclasses
from enum import Enum, auto
from glob import glob
from typing import List, Tuple
import matplotlib.pyplot as plt

import h5py
import numpy as np
from scipy import io as spio
from shapely import geometry


class RoiFileFormats(Enum):
    HDF = auto()
    HDFOutline = auto()
    MAT = auto()
    HDF2 = auto()


@dataclasses.dataclass(frozen=True)
class CameraCorrection:
    """linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc..."""
    darkCounts: float
    linearityPolynomial: typing.Tuple[float, ...] = None
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
    def __init__(self, name: str, number: int, mask: np.ndarray, verts: np.ndarray, filePath: str = None, fileFormat: RoiFileFormats = None):
        """A class representing a single ROI. consists of a name, a number, and a boolean mask array."""
        assert isinstance(mask, np.ndarray), f"data is a {type(mask)}"
        assert mask.dtype == np.bool
        self.verts = verts
        self.name = name
        self.number = number
        self.mask = mask
        self.filePath = filePath
        self.fileFormat = fileFormat

    @classmethod
    def fromVerts(cls, name: str, number: int, verts: np.ndarray, dataShape: tuple, filePath: str, fileFormat: RoiFileFormats):
        assert isinstance(verts, np.ndarray)
        assert isinstance(dataShape, tuple)
        assert len(dataShape) == 2
        assert verts.shape[1] == 2
        assert len(verts.shape) == 2
        x = np.arange(dataShape[1])
        y = np.arange(dataShape[0])
        X, Y = np.meshgrid(x, y)
        coords = list(zip(X.flatten(), Y.flatten()))
        matches = path.Path(verts).contains_points(coords)
        mask = matches.reshape(dataShape)
        return cls(name, number, mask, verts, filePath=filePath, fileFormat=fileFormat)

    @classmethod
    def fromHDF(cls, directory: str, name: str, number: int):
        path = os.path.join(directory, f'roi_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            return cls(name, number, mask=np.array(hf[str(number)]).astype(np.bool), verts=None, filePath=path, fileFormat=RoiFileFormats.HDF)

    @classmethod
    def fromHDF2(cls, directory: str, name: str, number: int):
        path = os.path.join(directory, f'ROI_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            return cls(name, number, mask=np.array(hf[str(number)]['mask']).astype(np.bool), verts=np.array(hf[str(number)]['verts']), filePath=path,
                       fileFormat=RoiFileFormats.HDF)

    @classmethod
    def fromHDFOutline(cls, directory: str, name: str, number: int):
        path = os.path.join(directory, f'roiV_{name}.h5')
        if not os.path.exists(path):
            raise OSError(f"File {path} does not exist.")
        with h5py.File(path, 'r') as hf:
            data = np.array(hf[str(number)]['verts'])
            shape = tuple(hf[str(number)]['dataShape'])
            return cls.fromVerts(name, number, data, shape, path, RoiFileFormats.HDFOutline)

    @classmethod
    def fromMat(cls, directory: str, name: str, number: int):
        filePath = os.path.join(directory, f'BW{number}_{name}.mat')
        return cls(name, number, mask=spio.loadmat(filePath)['BW'].astype(np.bool), verts=None, filePath=filePath, fileFormat=RoiFileFormats.MAT)

    @classmethod
    def loadAny(cls, directory: str, name: str, number: int):
        try:
            return Roi.fromHDF2(directory, name, number)
        except:
            try:
                return Roi.fromHDFOutline(directory, name, number)
            except:
                try:
                    return Roi.fromHDF(directory, name, number)
                except OSError: #For backwards compatibility purposes
                    return Roi.fromMat(directory, name, number)

    def toHDF(self, directory: str, overwrite: bool = False):
        savePath = os.path.join(directory, f'ROI_{self.name}.h5')
        with h5py.File(savePath, 'a') as hf:
            if np.string_(str(self.number)) in hf.keys():
                if overwrite:
                    del hf[np.string_(str(self.number))]
                else:
                    raise OSError(f"The Roi file {savePath} already contains a dataset {self.number}")
            g = hf.create_group(np.string_(str(self.number)))
            g.create_dataset(np.string_("verts"), data=self.verts.astype(np.float32))
            g.create_dataset(np.string_("mask"), data=self.mask.astype(np.uint8), compression=5)
        self.filePath = savePath
        self.fileFormat = RoiFileFormats.HDF2

    def deleteRoi(self, directory: str, name: str, num: int):
        path = os.path.join(directory, f"ROI_{name}.h5")
        if not os.path.exists(path):
            raise OSError(f"The file {path} does not exist.")
        with h5py.File(path, 'a') as hf:
            if np.string_(str(num)) not in hf.keys():
                raise ValueError(f"The file {path} does not contain ROI number {num}.")
            del hf[np.string_(str(num))]
            remaining = len(list(hf.keys()))
        if remaining == 0: #  If the file is empty then remove it.
            os.remove(path)

    @staticmethod
    def getValidRoisInPath(path: str) -> List[Tuple[str, int, RoiFileFormats]]:
        patterns = [('BW*_*.mat', RoiFileFormats.MAT), ('roi_*.h5', RoiFileFormats.HDF), ('roiV_*.h5', RoiFileFormats.HDFOutline)]
        files = {fformat: glob(os.path.join(path, p)) for p, fformat in patterns} #Lists of the found files keyed by file format
        ret = []
        for fformat, fileNames in files.items():
            if fformat == RoiFileFormats.HDF:
                for i in fileNames:
                    with h5py.File(i) as hf:
                        for g in hf.keys():
                            if isinstance(hf[g], h5py.Group): #Current file format
                                if 'mask' in hf[g] and 'verts' in hf[g]:
                                    name = i.split("ROI_")[-1][:-3]
                                    try:
                                        ret.append((name, int(g), RoiFileFormats.HDF2))
                                    except ValueError:
                                        print(f"Warning: File {i} contains uninterpretable dataset named {g}")
                                else:
                                    raise ValueError("File is missing datasets")
                            elif isinstance(hf[g], h5py.Dataset): #Legacy format
                                name = i.split('roi_')[-1][:-3]
                                try:
                                    ret.append((name, int(g), RoiFileFormats.HDF))
                                except ValueError:
                                    print(f"Warning: File {i} contains uninterpretable dataset named {g}")
            elif fformat == RoiFileFormats.HDFOutline:
                for i in fileNames:
                    name = i.split('roiV_')[-1][:-3]
                    with h5py.File(i) as hf:
                        for g in hf.keys():
                            if 'verts' in hf[g]:
                                try:
                                    ret.append((name, int(g), RoiFileFormats.HDFOutline))
                                except ValueError:
                                    print(f"Warning: File {i} contains uninterpretable dataset named {g}")

            elif fformat == RoiFileFormats.MAT:
                for i in fileNames: #list in files
                    i = os.path.split(i)[-1]
                    num = int(i.split('_')[0][2:])
                    name = i.split('_')[1][:-4]
                    ret.append((name, num, RoiFileFormats.MAT))
        return ret

    def transform(self, matrix: np.ndarray) -> Roi:
        """return a copy of this Roi that has been transformed by an affine transform matrix like the one returned by
        opencv.estimateRigidTransform. This can be obtained using ICBase's getTransform method."""
        import cv2
        mask = cv2.warpAffine(self.mask.astype(np.uint8), matrix, self.mask.shape).astype(np.bool)
        if self.verts is not None: verts = cv2.transform(self.verts, matrix)
        else: verts = None
        return Roi(self.name, self.number, mask=mask, verts=verts) #intentionally ditching the filepath and fileformat data here.

    def getImage(self, ax: plt.Axes):
        arr = self.mask.astype(np.uint8)*255
        arr = np.ma.masked_array(arr, arr == 0)
        im = ax.imshow(arr, alpha=0.5, clim=[0, 400], cmap='Reds')
        return im

    def getBoundingPolygon(self):
        if self.verts is None: # calculate convex hull
            x = np.arange(self.mask.shape[1])
            y = np.arange(self.mask.shape[0])
            X, Y = np.meshgrid(x, y)
            X = X[self.mask]
            Y = Y[self.mask]
            coords = list(zip(X, Y))
            g = geometry.Polygon(coords)
            return patches.Polygon(list(g.convex_hull.exterior.coords), facecolor=(1, 0, 0, 0.5))
        else:
            return patches.Polygon(self.verts, facecolor=(1, 0, 0, 0.5))
