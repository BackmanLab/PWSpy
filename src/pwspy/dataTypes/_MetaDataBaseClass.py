import jsonschema
from datetime import datetime
from pwspy.moduleConsts import dateTimeFormat
from ._otherClasses import CameraCorrection, Roi
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
import os, sys, subprocess
import h5py
import json
import numpy as np
from . import _jsonSchemasPath
import pathlib

class MetaDataBase(ABC):
    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'MetaDataBase.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, metadata: dict, filePath: Optional[str] = None):
        self.filePath = filePath
        refResolver = jsonschema.RefResolver(pathlib.Path(self._jsonSchemaPath).as_uri(), None)  # This resolver is used to allow derived json schemas to refer to the base schema.
        jsonschema.validate(instance=metadata, schema=self._jsonSchema, types={'array': (list, tuple)}, resolver=refResolver)
        self._dict: dict = metadata
        try:
            datetime.strptime(self._dict['time'], dateTimeFormat)
        except ValueError:
            try:
                print("Detected a non-compliant timestamp. attempting to correct.")
                self._dict['time'] = datetime.strftime(datetime.strptime(self._dict['time'], "%d-%m-%y %H:%M:%S"), dateTimeFormat)
            except ValueError:
                raise ValueError("The time stamp could not be parsed.")
        if self._dict['system'] == "":
            print("Warning: The `system` name in the metadata is blank. Check that the PWS System is saving the proper calibration values.")
        if all([i in self._dict for i in ['darkCounts', 'linearityPoly']]):
            if self._dict['darkCounts'] == 0:
                print("Warning: Detected a darkCounts value of 0 in the ImCube Metadata. Check that the PWS System is saving the proper calibration values.")
            self.cameraCorrection = CameraCorrection(darkCounts=self._dict['darkCounts'],
                                                     linearityPolynomial=self._dict['linearityPoly'])
        else:
            self.cameraCorrection = None

    @abstractmethod
    def idTag(self):
        pass

    @property
    def binning(self) -> int:
        return self._dict['binning']

    @property
    def pixelSizeUm(self) -> float:
        return self._dict['pixelSizeUm']

    @property
    def exposure(self) -> float:
        return self._dict['exposure']

    @property
    def time(self) -> str:
        return self._dict['time']

    def getRois(self) -> List[Tuple[str, int, Roi.FileFormats]]:
        assert self.filePath is not None
        return Roi.getValidRoisInPath(self.filePath)

    def loadRoi(self, name: str, num: int, fformat: Roi.FileFormats = None) -> Roi:
        if fformat == Roi.FileFormats.MAT:
            return Roi.fromMat(self.filePath, name, num)
        elif fformat == Roi.FileFormats.HDF:
            return Roi.fromHDF(self.filePath, name, num)
        else:
            return Roi.loadAny(self.filePath, name, num)

    def saveRoi(self, roi: Roi, overwrite: bool = False) -> None:
        roi.toHDF(self.filePath, overwrite=overwrite)

    def deleteRoi(self, name: str, num: int):
        Roi.deleteRoi(self.filePath, name, num)

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

    @staticmethod
    def _decodeHdfMetadata(d: h5py.Dataset) -> dict:
        assert 'metadata' in d.attrs
        return json.loads(d.attrs['metadata'])

    def encodeHdfMetadata(self, d: h5py.Dataset) -> h5py.Dataset:
        d.attrs['metadata'] = np.string_(json.dumps(self._dict))
        return d
