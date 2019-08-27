from __future__ import annotations
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
import typing
if typing.TYPE_CHECKING:
    from ._AcqDir import AcqDir

class MetaDataBase(ABC):
    """This base class provides that basic functionality to store information about a PWS related acquisition on file."""
    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'MetaDataBase.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)  # This serves as a schematic that can be checked against when loading metadata to make sure it contains the required information.

    def __init__(self, metadata: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        self.filePath = filePath
        self.acquisitionDirectory = acquisitionDirectory
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
        """Return a string that uniquely identifies this data."""
        pass

    @property
    def binning(self) -> int:
        """The binning setting used by the camera. This is needed in order to properly correct dark counts.
        This is generally extracted from metadata saved by Micromanager"""
        return self._dict['binning']

    @property
    def pixelSizeUm(self) -> float:
        """The pixelSize expressed in microns. This represents the length of each square pixel in object space. Binning
        has already been accounted for here. This is generally extracted from metadata saved my MicroManager"""
        return self._dict['pixelSizeUm']

    @property
    def exposure(self) -> float:
        """The exposure time of the camera expressed in milliseconds."""
        return self._dict['exposure']

    @property
    def time(self) -> str:
        """The date and time that the acquisition was taken."""
        return self._dict['time']


    @staticmethod
    def _decodeHdfMetadata(d: h5py.Dataset) -> dict:
        """Attempt to extract a dictionary of metadata from an HDF5 dataset."""
        assert 'metadata' in d.attrs
        return json.loads(d.attrs['metadata'])

    def encodeHdfMetadata(self, d: h5py.Dataset) -> h5py.Dataset:
        """Save this metadata object as a json string in an HDF5 dataset."""
        d.attrs['metadata'] = np.string_(json.dumps(self._dict))
        return d
