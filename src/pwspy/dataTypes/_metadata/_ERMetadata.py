import json
import os
from typing import Tuple, Union

import h5py
import jsonschema
import numpy as np


class ERMetaData:
    """A class representing the extra information related to an ExtraReflectanceCube file. This can be useful as a object
     to keep track of a ExtraReflectanceCube without having to have the data from the file loaded into memory."""
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'extraReflectionMetadataSchema',
                   'title': 'extraReflectionMetadataSchema',
                   'required': ['system', 'time', 'wavelengths', 'pixelSizeUm', 'binning', 'numericalAperture'],
                   'type': 'object',
                   'properties': {
                       'system': {'type': 'string'},
                       'time': {'type': 'string'},
                       'wavelengths': {'type': 'array',
                                        'items': {'type': 'number'}
                                        },
                       'pixelSizeUm': {'type': ['number', 'null']},
                       'binning': {'type': ['integer', 'null']},
                       'numericalAperture': {'type': ['number']}
                        }
                   }
    _FILESUFFIX = '_eReflectance.h5'
    _DATASETTAG = 'extraReflection'
    _MDTAG = 'metadata'

    def __init__(self, inheritedMetadata: dict, numericalAperture: float, filePath: str=None):
        """The metadata dictionary will often just be inherited information from one of the ImCubes that was used to create
        this ER Cube. While this data can be useful it should be taken with a grain of salt. E.G. the metadata will contain
        an `exposure` field. In reality this ER Cube will have been created from ImCubes at a variety of exposures."""
        self.inheritedMetadata = inheritedMetadata
        self.inheritedMetadata['numericalAperture'] = numericalAperture
        jsonschema.validate(instance=inheritedMetadata, schema=self._jsonSchema, types={'array': (list, tuple)})
        self.filePath = filePath

    @property
    def idTag(self):
        return f"ExtraReflection_{self.inheritedMetadata['system']}_{self.inheritedMetadata['time']}"

    @property
    def numericalAperture(self):
        return self.inheritedMetadata['numericalAperture']

    @property
    def systemName(self) -> str:
        return self.inheritedMetadata['system']

    @classmethod
    def validPath(cls, path: str) -> Tuple[bool, Union[str, bytes], Union[str, bytes]]:
        if cls._FILESUFFIX in path:
            directory, name = cls.directory2dirName(path)
            with h5py.File(os.path.join(directory, f'{name}{cls._FILESUFFIX}'), 'r') as hf:
                valid = cls._MDTAG in hf[cls._DATASETTAG].attrs
            return valid, directory, name
        else:
            return False, '', ''

    @classmethod
    def fromHdfFile(cls, directory: str, name: str):
        filePath = cls.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[cls._DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None):
        mdDict = json.loads(d.attrs[cls._MDTAG])
        return cls(mdDict, mdDict['numericalAperture'], filePath=filePath)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        g[self._DATASETTAG].attrs[self._MDTAG] = np.string_(json.dumps(self.inheritedMetadata))
        return g

    @classmethod
    def directory2dirName(cls, path: str) -> Tuple[Union[bytes, str], Union[bytes, str]]:
        directory, fileName = os.path.split(path)
        name = fileName.split(cls._FILESUFFIX)[0]
        return directory, name

    @classmethod
    def dirName2Directory(cls, directory: str, name: str):
        return os.path.join(directory, f'{name}{cls._FILESUFFIX}')