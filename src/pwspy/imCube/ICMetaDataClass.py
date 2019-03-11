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
from enum import Enum, auto
from typing import Optional, List, Tuple

import jsonschema
import scipy.io as spio
import tifffile as tf

from pwspy.analysis import AnalysisResults
from pwspy.analysis.analysisResults import LazyAnalysisResultsLoader
from pwspy.imCube.otherClasses import Roi
from .otherClasses import CameraCorrection


class ICFileFormats(Enum):
    RawBinary = auto()
    Tiff = auto()


class ICMetaData:
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'ICMetadataSchema',
                   'title': 'ICMetadataSchema',
                   'type': 'object',
                   'required': ['system', 'time', 'exposure', 'wavelengths'],
                   'properties': {
                       'system': {'type': 'string'},
                       'time': {'type': 'string'},
                       'exposure': {'type': 'number'},
                       'wavelengths': {'type': 'array',
                                       'items': {'type': 'number'}
                                       }
                        }
                   }

    def __init__(self, metadata: dict, filePath: str = None, fileFormat: ICFileFormats = None):
        jsonschema.validate(instance=metadata, schema=self._jsonSchema)
        self.metadata: dict = metadata
        self.filePath: Optional[str] = filePath
        self.fileFormat: ICFileFormats = fileFormat
        if all([i in self.metadata for i in ['darkCounts', 'linearityPoly']]):
            self.cameraCorrection = CameraCorrection(darkCounts=self.metadata['darkCounts'],
                                                     linearityPolynomial=self.metadata['linearityPoly'])
        else:
            self.cameraCorrection = None

    @property
    def idTag(self):
        #TODO math operations on the cube should mangle this somehow so that a modified cube wouldn't be saved with a duplicate id.
        return f"{self.metadata['system']}_{self.metadata['time']}"

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
            wv = list(spio.loadmat(os.path.join(directory, 'WV.mat'))['WV'].squeeze())
            wv = [int(i) for i in wv]  # We will have issues saving later if these are numpy int types.
            md = {'startWv': info2[0], 'stepWv': info2[1], 'stopWv': info2[2],
                  'exposure': info2[3], 'time': '{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(
                    *[int(i) for i in [info3[8], info3[7], info3[6], info3[9], info3[10], info3[11]]]),
                  'systemId': info3[0], 'system': str(info3[0]),
                  'imgHeight': int(info3[2]), 'imgWidth': int(info3[3]), 'wavelengths': wv}
        return cls(md, filePath=directory, fileFormat=ICFileFormats.RawBinary)

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
        return cls(metadata, filePath=directory, fileFormat=ICFileFormats.Tiff)

    @staticmethod
    def _checkMetadata(metadata: dict):
        required = {'time', 'exposure', 'wavelengths', 'system'}
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

    def hasNotes(self) -> bool:
        return os.path.exists(os.path.join(self.filePath, 'notes.txt'))

    def getNotes(self) -> str:
        if self.hasNotes():
            with open(os.path.join(self.filePath, 'notes.txt'), 'r') as f:
                return f.readlines().join('\n')
        else:
            return ''
