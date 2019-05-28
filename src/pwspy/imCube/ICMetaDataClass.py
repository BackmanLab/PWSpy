# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 19:17:14 2019

@author: Nick
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import typing
from enum import Enum, auto
from typing import Optional, List, Tuple

import h5py
import jsonschema
import scipy.io as spio
import tifffile as tf

from pwspy.moduleConsts import dateTimeFormat
from pwspy.utility.misc import cached_property
if typing.TYPE_CHECKING:
    from pwspy.analysis import AnalysisResultsSaver
    import multiprocessing as mp
from pwspy.imCube.otherClasses import Roi, RoiFileFormats
from .otherClasses import CameraCorrection
import numpy as np
from datetime import datetime

class ICFileFormats(Enum):
    RawBinary = auto()
    Tiff = auto()
    Hdf = auto()
    NanoMat = auto()


class ICMetaData:
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'ICMetadataSchema',
                   'title': 'ICMetadataSchema',
                   'type': 'object',
                   'required': ['system', 'time', 'exposure', 'wavelengths', 'pixelSizeUm', 'binning'],
                   'properties': {
                       'system': {'type': 'string'},
                       'time': {'type': 'string'},
                       'exposure': {'type': 'number'},
                       'wavelengths': {'type': 'array',
                                       'items': {'type': 'number'}
                                       },
                       'pixelSizeUm': {'type': ['number', 'null']},
                       'binning': {'type': ['integer', 'null']}
                       }
                   }

    def __init__(self, metadata: dict, filePath: str = None, fileFormat: ICFileFormats = None):
        jsonschema.validate(instance=metadata, schema=self._jsonSchema, types={'array': (list, tuple)})
        self._dict: dict = metadata
        self.filePath: Optional[str] = filePath
        self.fileFormat: ICFileFormats = fileFormat
        self._dict['wavelengths'] = tuple(np.array(self._dict['wavelengths']).astype(float))
        try:
            datetime.strptime(self._dict['time'], dateTimeFormat)
        except ValueError:
            try:
                print("Detected a non-compliant timestamp. attempting to correct.")
                self._dict['time'] = datetime.strftime(datetime.strptime(self._dict['time'], "%d-%m-%y %H:%M:%S"), dateTimeFormat)
            except ValueError:
                raise ValueError("The time stamp could not be parsed.")
        if all([i in self._dict for i in ['darkCounts', 'linearityPoly']]):
            self.cameraCorrection = CameraCorrection(darkCounts=self._dict['darkCounts'],
                                                     linearityPolynomial=self._dict['linearityPoly'])
        else:
            self.cameraCorrection = None

    @cached_property
    def idTag(self) -> str:
        return f"ImCube_{self._dict['system']}_{self._dict['time']}"

    @property
    def binning(self) -> int:
        return self._dict['binning']

    @property
    def pixelSizeUm(self) -> float:
        return self._dict['pixelSizeUm']

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self._dict['wavelengths']

    @property
    def exposure(self) -> float:
        return self._dict['exposure']

    @property
    def time(self) -> str:
        return self._dict['time']

    @classmethod
    def loadAny(cls, directory, lock: mp.Lock = None):
        try:
            return ICMetaData.fromTiff(directory, lock=lock)
        except:
            try:
                return ICMetaData.fromOldPWS(directory, lock=lock)
            except:
                try:
                    return ICMetaData.fromNano(directory, lock=lock)
                except:
                    raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory, lock: mp.Lock = None):
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
        return cls(md, filePath=directory, fileFormat=ICFileFormats.RawBinary)

    @classmethod
    def fromNano(cls, directory: str, lock: mp.Lock = None):
        if lock is not None:
            lock.acquire()
        try:
            with h5py.File(os.path.join(directory, 'imageCube.mat'), 'r') as hf:
                cubeParams = hf['cubeParameters']
                lam = cubeParams['lambda']
                exp = cubeParams['exposure'] #TODO we don't support adaptive exposure.
                md = {'startWv': lam['start'].value[0][0], 'stepWv': lam['step'].value[0][0], 'stopWv': lam['stop'].value[0][0],
                      'exposure': exp['base'].value[0][0], 'time': datetime.strptime(np.string_(cubeParams['metadata']['date'].value.astype(np.uint8)).decode(), '%Y%m%dT%H%M%S').strftime(dateTimeFormat),
                      'system': np.string_(cubeParams['metadata']['hardware']['system']['id'].value.astype(np.uint8)).decode(), 'wavelengths': list(lam['sequence'].value[0]),
                      'binning': None, 'pixelSizeUm': None}
        finally:
            if lock is not None:
                lock.release()
        return cls(md, filePath=directory, fileFormat=ICFileFormats.NanoMat)

    @classmethod
    def fromTiff(cls, directory, lock: mp.Lock = None):
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
        if 'waveLengths' in metadata:
            metadata['wavelengths'] = metadata['waveLengths']
            del metadata['waveLengths']
        return cls(metadata, filePath=directory, fileFormat=ICFileFormats.Tiff)

    def metadataToJson(self, directory):
        with open(os.path.join(directory, 'pwsmetadata.json'), 'w') as f:
            json.dump(self._dict, f)

    def getRois(self) -> List[Tuple[str, int, RoiFileFormats]]:
        assert self.filePath is not None
        return Roi.getValidRoisInPath(self.filePath)

    def loadRoi(self, name: str, num: int, fformat: RoiFileFormats = None) -> Roi:
        if fformat == RoiFileFormats.MAT:
            return Roi.fromMat(self.filePath, name, num)
        elif fformat == RoiFileFormats.HDF:
            return Roi.fromHDF(self.filePath, name, num)
        else:
            return Roi.loadAny(self.filePath, name, num)

    def saveRoi(self, roi: Roi, overwrite: bool = False) -> None:
        roi.toHDF(self.filePath, overwrite=overwrite)

    def deleteRoi(self, name: str, num: int):
        Roi.deleteRoi(self.filePath, name, num)


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
        return AnalysisResultsLoader(os.path.join(self.filePath, 'analyses'), name)

    def removeAnalysis(self, name: str):
        os.remove(os.path.join(self.filePath, 'analyses', AnalysisResultsLoader.name2FileName(name)))

    def editNotes(self):
        filepath = os.path.join(self.filePath, 'notes.txt')
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                pass
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name == 'nt':  # For Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # For Linux, Mac, etc.
            subprocess.call(('xdg-open', filepath))

    def hasNotes(self) -> bool:
        return os.path.exists(os.path.join(self.filePath, 'notes.txt'))

    def getNotes(self) -> str:
        if self.hasNotes():
            with open(os.path.join(self.filePath, 'notes.txt'), 'r') as f:
                return '\n'.join(f.readlines())
        else:
            return ''

    @classmethod
    def _decodeHdfMetadata(cls, d: h5py.Dataset) -> dict:
        assert 'metadata' in d.attrs
        return json.loads(d.attrs['metadata'])

    @classmethod
    def fromHdf(cls, d: h5py.Dataset):
        return cls(cls._decodeHdfMetadata(d), fileFormat=ICFileFormats.Hdf)

    def encodeHdfMetadata(self, d: h5py.Dataset) -> h5py.Dataset:
        d.attrs['metadata'] = np.string_(json.dumps(self._dict))
        return d

    def getImBd(self) -> np.ndarray:
        if self.fileFormat == ICFileFormats.NanoMat:
            with h5py.File(os.path.join(self.filePath, 'image_bd.mat'), 'r') as hf:
                return np.array(hf['image_bd'])
        else:
            with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
                return f.asarray()

from pwspy.analysis.analysisResults import AnalysisResultsLoader
