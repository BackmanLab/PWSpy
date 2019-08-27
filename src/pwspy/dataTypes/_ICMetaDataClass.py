# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 19:17:14 2019

@author: Nick Anthony
"""
from __future__ import annotations

from dataTypes import AcqDir
from pwspy.dataTypes._FluoresenceImg import FluorescenceImage
from ._MetaDataBaseClass import MetaDataBase
from . import _jsonSchemasPath
from pwspy.moduleConsts import dateTimeFormat
from pwspy.utility.misc import cached_property
from pwspy.analysis import AnalysisResultsSaver, AnalysisResultsLoader
import json
import os
from enum import Enum, auto
from typing import Optional, List, Tuple
import h5py
import scipy.io as spio
import tifffile as tf
import numpy as np
from datetime import datetime
import typing
if typing.TYPE_CHECKING:
    import multiprocessing as mp


class ICMetaData(MetaDataBase): #TODO this currently encapsulates PWS specific funcitonality as well as PWS/Dyn/Fluore/Analysis folder stuff. should be separated into two classes.
    class FileFormats(Enum):
        RawBinary = auto()
        Tiff = auto()
        Hdf = auto()
        NanoMat = auto()

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'ICMetaData.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, metadata: dict, filePath: Optional[str] = None, fileFormat: ICMetaData.FileFormats = None, acquisitionDirectory: Optional[AcqDir] = None):
        super().__init__(metadata, filePath, acquisitionDirectory=acquisitionDirectory)
        self.fileFormat: ICMetaData.FileFormats = fileFormat
        self._dict['wavelengths'] = tuple(np.array(self._dict['wavelengths']).astype(float))


    @cached_property
    def idTag(self) -> str:
        return f"ImCube_{self._dict['system']}_{self._dict['time']}"

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self._dict['wavelengths']

    @classmethod
    def loadAny(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None):
        try:
            return ICMetaData.fromTiff(directory, lock=lock, acquisitionDirectory=acquisitionDirectory)
        except:
            try:
                return ICMetaData.fromOldPWS(directory, lock=lock, acquisitionDirectory=acquisitionDirectory)
            except:
                try:
                    return ICMetaData.fromNano(directory, lock=lock, acquisitionDirectory=acquisitionDirectory)
                except:
                    raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None):
        if lock is not None:
            lock.acquire()
        try:
            try:
                md = json.load(open(os.path.join(directory, 'pwsmetadata.txt')))
            except:  # have to use the old metadata
                print("Json metadata not found. Using backup metadata.")
                info2 = list(spio.loadmat(os.path.join(directory, 'info2.mat'))['info2'].squeeze())
                info3 = list(spio.loadmat(os.path.join(directory, 'info3.mat'))['info3'].squeeze())
                wv = list(spio.loadmat(os.path.join(directory, 'WV.mat'))['WV'].squeeze())
                wv = [int(i) for i in wv]  # We will have issues saving later if these are numpy int types.
                md = {'startWv': info2[0], 'stepWv': info2[1], 'stopWv': info2[2],
                      'exposure': info2[3], 'time': '{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(
                        *[int(i) for i in [info3[8], info3[7], info3[6], info3[9], info3[10], info3[11]]]),
                      'systemId': info3[0], 'system': str(info3[0]),
                      'imgHeight': int(info3[2]), 'imgWidth': int(info3[3]), 'wavelengths': wv,
                      'binning': None, 'pixelSizeUm': None}
        finally:
            if lock is not None:
                lock.release()
        return cls(md, filePath=directory, fileFormat=ICMetaData.FileFormats.RawBinary, acquisitionDirectory=acquisitionDirectory)

    @classmethod
    def fromNano(cls, directory: str, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None):
        if lock is not None:
            lock.acquire()
        try:
            with h5py.File(os.path.join(directory, 'imageCube.mat'), 'r') as hf:
                cubeParams = hf['cubeParameters']
                lam = cubeParams['lambda']
                exp = cubeParams['exposure'] #we don't support adaptive exposure.
                md = {'startWv': lam['start'].value[0][0], 'stepWv': lam['step'].value[0][0], 'stopWv': lam['stop'].value[0][0],
                      'exposure': exp['base'].value[0][0], 'time': datetime.strptime(np.string_(cubeParams['metadata']['date'].value.astype(np.uint8)).decode(), '%Y%m%dT%H%M%S').strftime(dateTimeFormat),
                      'system': np.string_(cubeParams['metadata']['hardware']['system']['id'].value.astype(np.uint8)).decode(), 'wavelengths': list(lam['sequence'].value[0]),
                      'binning': None, 'pixelSizeUm': None}
        finally:
            if lock is not None:
                lock.release()
        return cls(md, filePath=directory, fileFormat=ICMetaData.FileFormats.NanoMat, acquisitionDirectory=acquisitionDirectory)

    @classmethod
    def fromTiff(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None):
        if lock is not None:
            lock.acquire()
        try:
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
                        metadata = json.loads(tif.imagej_metadata['Info'])  # The micromanager plugin saves metadata as the info property of the imagej imageplus object.
                    metadata['time'] = tif.pages[0].tags['DateTime'].value
        finally:
            if lock is not None:
                lock.release()
        #For a while the micromanager metadata was getting saved weird this fixes it.
        if 'major_version' in metadata['MicroManagerMetadata']:
            metadata['MicroManagerMetadata'] = metadata['MicroManagerMetadata']['map']
        # Get binning from the micromanager metadata
        binning = metadata['MicroManagerMetadata']['Binning']
        if isinstance(binning, dict):  # This is due to a property map change from beta to gamma
            binning = binning['scalar']
        metadata['binning'] = binning
        # Get the pixel size from the micromanager metadata
        metadata['pixelSizeUm'] = metadata['MicroManagerMetadata']['PixelSizeUm']['scalar']
        if metadata['pixelSizeUm'] == 0: metadata['pixelSizeUm'] = None
        if 'waveLengths' in metadata:  # Fix an old naming issue
            metadata['wavelengths'] = metadata['waveLengths']
            del metadata['waveLengths']
        return cls(metadata, filePath=directory, fileFormat=ICMetaData.FileFormats.Tiff, acquisitionDirectory=acquisitionDirectory)

    def metadataToJson(self, directory):
        with open(os.path.join(directory, 'pwsmetadata.json'), 'w') as f:
            json.dump(self._dict, f)

    def getAnalyses(self) -> typing.List[str]:
        assert self.filePath is not None
        return self.getAnalysesAtPath(self.filePath)

    @staticmethod
    def getAnalysesAtPath(path: str) -> typing.List[str]:
        anPath = os.path.join(path, 'analyses')
        if os.path.exists(anPath):
            files = os.listdir(os.path.join(path, 'analyses'))
            return [AnalysisResultsLoader.fileName2Name(f) for f in files]
        else:
            # print(f"ImCube at {path} has no `analyses` folder.")
            return []

    def saveAnalysis(self, analysis: AnalysisResultsSaver, name:str):
        path = os.path.join(self.filePath, 'analyses')
        if not os.path.exists(path):
            os.mkdir(path)
        analysis.toHDF5(path, name)

    def loadAnalysis(self, name: str) -> AnalysisResultsLoader:
        from pwspy.analysis import AnalysisResultsLoader
        return AnalysisResultsLoader(os.path.join(self.filePath, 'analyses'), name)

    def removeAnalysis(self, name: str):
        from pwspy.analysis import AnalysisResultsLoader
        os.remove(os.path.join(self.filePath, 'analyses', AnalysisResultsLoader.name2FileName(name)))

    @classmethod
    def fromHdf(cls, d: h5py.Dataset):
        return cls(cls._decodeHdfMetadata(d), fileFormat=ICMetaData.FileFormats.Hdf)

    def getThumbnail(self) -> np.ndarray:
        if self.fileFormat == ICMetaData.FileFormats.NanoMat:
            with h5py.File(os.path.join(self.filePath, 'image_bd.mat'), 'r') as hf:
                return np.array(hf['image_bd'])
        else:
            with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
                return f.asarray()

