# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 19:17:14 2019

@author: Nick
"""
import json
import os
import subprocess
import sys
import typing
from glob import glob
from typing import Optional, Union, List, Tuple
import re

import h5py
import numpy as np
import scipy.io as spio
import tifffile as tf

from pwspy.analysis import AnalysisResults
from pwspy.analysis.analysisResults import LazyAnalysisResultsLoader
from .otherClasses import CameraCorrection


class ICMetaData:
    filePath: Optional[str]
    metadata: dict

    def __init__(self, metadata: dict, filePath: str=None):
        self._checkMetadata(metadata)
        self.metadata = metadata
        self.filePath = filePath
        if all([i in self.metadata for i in ['darkCounts', 'linearityPoly']]):
            self.cameraCorrection = CameraCorrection(darkCounts=self.metadata['darkCounts'],
                                                     linearityPolynomial=self.metadata['linearityPoly'])
        else:
            self.cameraCorrection = None

    @property
    def idTag(self):
        return f"{self.metadata['time']}"  # TODO finish this

    @classmethod
    def loadAny(cls, directory):
        try:
            return ICMetaData.fromTiff(directory)
        except:
            try:
                return ICMetaData.fromOldPWS(directory)
            except:
                raise Exception(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory):
        try:
            md = json.load(open(os.path.join(directory, 'pwsmetadata.txt')))
        except:  # have to use the old metadata
            print("Json metadata not found")
            info2 = list(spio.loadmat(os.path.join(directory, 'info2.mat'))['info2'].squeeze())
            info3 = list(spio.loadmat(os.path.join(directory, 'info3.mat'))['info3'].squeeze())
            wv = list(spio.loadmat(os.path.join(directory, 'wv.mat'))['WV'].squeeze())
            wv = [int(i) for i in wv]  # We will have issues saving later if these are numpy int types.
            md = {'startWv': info2[0], 'stepWv': info2[1], 'stopWv': info2[2],
                  'exposure': info2[3], 'time': '{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(
                    *[int(i) for i in [info3[8], info3[7], info3[6], info3[9], info3[10], info3[11]]]),
                  'systemId': info3[0],
                  'imgHeight': int(info3[2]), 'imgWidth': int(info3[3]), 'wavelengths': wv}
        return cls(md, filePath=directory)

    @classmethod
    def fromTiff(cls, directory):
        if os.path.exists(os.path.join(directory, 'MMStack.ome.tif')):
            path = os.path.join(directory, 'MMStack.ome.tif')
        elif os.path.exists(os.path.join(directory, 'pws.tif')):
            path = os.path.join(directory, 'pws.tif')
        else:
            raise OSError("No Tiff file was found at:", directory)
        if os.path.exists(os.path.join(directory, 'pwsmetadata.json')):
            metadata = json.load(open(os.path.join(directory, 'pwsmetadata.json'), 'r'))
        else:
            with tf.TiffFile(path) as tif:
                try:
                    metadata = json.loads(tif.pages[0].description)
                except:
                    metadata = json.loads(tif.imagej_metadata[
                                              'Info'])  # The micromanager plugin saves metadata as the info property of the imagej imageplus object.
                metadata['time'] = tif.pages[0].tags['DateTime'].value
        if 'waveLengths' in metadata:
            metadata['wavelengths'] = metadata['waveLengths']
            del metadata['waveLengths']
        return cls(metadata, filePath=directory)

    @staticmethod
    def _checkMetadata(metadata: dict):
        required = ['time', 'exposure', 'wavelengths']
        for i in required:
            if i not in metadata:
                raise ValueError(f"Metadata does not have a '{i}' field.")

    def toJson(self, directory):
        with open(os.path.join(directory, 'pwsmetadata.json'), 'w') as f:
            json.dump(self.metadata, f)

    def getRois(self) -> List[Tuple[str, int]]:
        assert self.filePath is not None
        return Roi.getValidRoisInPath(self.filePath)

    def getAnalyses(self):
        assert self.filePath is not None
        return self.getAnalysesAtPath(self.filePath)

    @staticmethod
    def getAnalysesAtPath(path: str) -> typing.List[str]:
        anPath = os.path.join(path, 'analyses')
        if os.path.exists(anPath):
            return os.listdir(os.path.join(path, 'analyses'))
        else:
            return []

    def saveAnalysis(self, analysis: AnalysisResults, name:str):
        analysis.toHDF5(os.path.join(self.filePath, 'analyses'), name)

    def loadAnalysis(self, name: str) -> LazyAnalysisResultsLoader:
        return LazyAnalysisResultsLoader(os.path.join(self.filePath, 'analyses'), name)

    def editNotes(self):
        filepath = os.path.join(self.filePath, 'notes.txt.')
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                pass
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name == 'nt':  # For Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # For Linux, Mac, etc.
            subprocess.call(('xdg-open', filepath))


class Roi:
    def __init__(self, name:str, number: int, data: np.ndarray, filePath: str = None):
        assert data.dtype == np.bool
        self.data = data
        self.name = name
        self.number = number
        self.filePath = filePath

    @classmethod
    def fromHDF(cls, directory: str, name: str, number: int):
        filePath = os.path.join(directory, f'roi{number}_{name}.h5')
        with h5py.File(filePath) as hf:
            return cls(name, number, hf['data'], filePath=filePath)

    @classmethod
    def fromMat(cls, directory: str, name: str, number: int):
        filePath = os.path.join(directory, f'BW{number}_{name}.mat')
        return cls(name, number,
                   spio.loadmat(filePath)['BW'].astype(np.bool),
                   filePath= filePath)

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
            if any([re.match(pattern, fname) is not None for pattern in ["BW.+_.+\.mat", "roi.+_.+\.h5"]]):
                ret.append(('_'.join(fname.split('_')[1:]).split('.')[0], int(fname.split('_')[0][2:])))
        return ret
