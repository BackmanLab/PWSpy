from __future__ import annotations
import json
from datetime import datetime
from typing import Tuple, Union

import h5py
import jsonschema

from pwspy.imCube.ICBaseClass import ICBase
import numpy as np
import os
from pwspy.moduleConsts import dateTimeFormat
import typing
import pandas as pd
if typing.TYPE_CHECKING:
    from pwspy.imCube import ImCube

class ERMetadata:
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'extraReflectionMetadataSchema',
                   'title': 'extraReflectionMetadataSchema',
                   'required': ['system', 'time', 'wavelengths', 'pixelSizeUm', 'binning'],
                   'type': 'object',
                   'properties': {
                       'system': {'type': 'string'},
                       'time': {'type': 'string'},
                       'wavelengths': {'type': 'array',
                                        'items': {'type': 'number'}
                                        },
                       'pixelSizeUm': {'type': ['number', 'null']},
                       'binning': {'type': ['integer', 'null']}
                        }
                   }
    FILESUFFIX = '_eReflectance.h5'
    DATASETTAG = 'extraReflection'
    MDTAG = 'metadata'

    def __init__(self, inheritedMetadata: dict, filePath: str=None):
        """The metadata dictionary will often just be inherited information from one of the ImCubes that was used to create
        this ER Cube. While this data can be useful it should be taken with a grain of salt. E.G. the metadata will contain
        an `exposure` field. In reality this ER Cube will have been created from ImCubes at a variety of exposures."""
        self.inheritedMetadata = inheritedMetadata
        jsonschema.validate(instance=inheritedMetadata, schema=self._jsonSchema, types={'array': (list, tuple)})
        self.filePath = filePath

    @property
    def idTag(self):
        return f"ExtraReflection_{self.inheritedMetadata['system']}_{self.inheritedMetadata['time']}"

    @classmethod
    def validPath(cls, path: str) -> Tuple[bool, Union[str, bytes], Union[str, bytes]]:
        if cls.FILESUFFIX in path:
            directory, name = cls.directory2dirName(path)
            with h5py.File(os.path.join(directory, f'{name}{cls.FILESUFFIX}'), 'r') as hf:
                valid = cls.MDTAG in hf[cls.DATASETTAG].attrs
            return valid, directory, name
        else:
            return False, '', ''

    @classmethod
    def fromHdfFile(cls, directory: str, name: str):
        filePath = cls.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[cls.DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None):
        return cls(json.loads(d.attrs[cls.MDTAG]), filePath=filePath)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        g[self.DATASETTAG].attrs[self.MDTAG] = np.string_(json.dumps(self.inheritedMetadata))
        return g

    @classmethod
    def directory2dirName(cls, path: str) -> Tuple[Union[bytes, str], Union[bytes, str]]:
        directory, fileName = os.path.split(path)
        name = fileName.split(cls.FILESUFFIX)[0]
        return directory, name

    @classmethod
    def dirName2Directory(cls, directory: str, name: str):
        return os.path.join(directory, f'{name}{cls.FILESUFFIX}')

class ExtraReflectanceCube(ICBase):
    """This class builds upon ERMetadata to add data array operations."""
    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: ERMetadata):
        assert isinstance(metadata, ERMetadata)
        if data.max() > 1 or data.min() < 0:
            print("Warning!: Reflectance values must be between 0 and 1")
        self.metadata = metadata
        ICBase.__init__(self, data, wavelengths)

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self.index

    @classmethod
    def fromHdfFile(cls, directory: str, name: str) -> ExtraReflectanceCube:
        filePath = ERMetadata.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[ERMetadata.DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    def toHdfFile(self, directory: str, name: str) -> None:
        savePath = os.path.join(directory, f'{name}{ERMetadata.FILESUFFIX}')
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            self.toHdfDataset(hf)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        g = super().toHdfDataset(g, ERMetadata.DATASETTAG)
        g = self.metadata.toHdfDataset(g)
        return g

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None):
        data, index = cls._decodeHdf(d)
        md = ERMetadata.fromHdfDataset(d, filePath=filePath)
        return cls(data, index, md)

    @classmethod
    def fromMetadata(cls, md: ERMetadata):
        directory, name = ERMetadata.directory2dirName(md.filePath)
        return cls.fromHdfFile(directory, name)


class ExtraReflectionCube(ICBase):
    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: ERMetadata):
        super().__init__(data, wavelengths)
        self.metadata = metadata

    @classmethod
    def create(cls, reflectance: ExtraReflectanceCube, theoryR: pd.Series, reference: ImCube):
        I0 = reference.data / (theoryR[None, None, :] + reflectance.data) # I0 is the intensity of the illumination source, reconstructed in units of `counts`. this is an inversion of our assumption that reference = I0*(referenceReflectance + extraReflectance)
        data = reflectance.data * I0  # converting extraReflectance to the extra reflection in units of counts
        return cls(data, reflectance.wavelengths, reflectance.metadata)
