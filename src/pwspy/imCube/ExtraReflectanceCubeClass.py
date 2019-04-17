import json
from datetime import datetime
from typing import Tuple, Union

import h5py
import jsonschema

from pwspy.imCube.ICBaseClass import ICBase
import numpy as np
import os
from pwspy.moduleConsts import dateTimeFormat


class ExtraReflectanceCube(ICBase):
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'extraReflectionMetadataSchema',
                   'title': 'extraReflectionMetadataSchema',
                   'required': ['system', 'time'],
                   'type': 'object',
                   'properties': {
                       'system': {'type': 'string'},
                       'time': {'type': 'string'}
                        }
                   }
    FILESUFFIX = '_eReflectance.h5'
    DATASETTAG = 'extraReflection'
    MDTAG = 'metadata'

    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], inheritedMetadata: dict):
        """The metadata dictionary will often just be inherited information from one of the ImCubes that was used to create
        this ER Cube. While this data can be useful it should be taken with a grain of salt. E.G. the metadata will contain
        an `exposure` field. In reality this ER Cube will have been created from ImCubes at a variety of exposures."""
        metadata = inheritedMetadata
        metadata['time'] = datetime.now().strftime(dateTimeFormat) #Save the current time
        jsonschema.validate(instance=metadata, schema=self._jsonSchema)
        if data.max() > 1 or data.min() < 0:
            print("Warning!: Reflectance values must be between 0 and 1")
        super().__init__(data, wavelengths)
        self.metadata = metadata

    @property
    def idTag(self):
        return f"ExtraReflection_{self.metadata['system']}_{self.metadata['time']}"

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self.index

    @classmethod
    def fromHdfFile(cls, directory: str, name: str):
        with h5py.File(os.path.join(directory, f'{name}{cls.FILESUFFIX}')) as hf:
            dset = hf[cls.DATASETTAG]
            return cls.fromHdfDataset(dset)

    def toHdfFile(self, directory: str, name: str) -> None:
        savePath = os.path.join(directory, f'{name}{self.FILESUFFIX}')
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            self.toHdfDataset(hf, name)

    def toHdfDataset(self, g: h5py.Group, name: str) -> h5py.Group:
        g = super().toHdfDataset(g, self.DATASETTAG)
        g[self.DATASETTAG].attrs[self.MDTAG] = np.string_(json.dumps(self.metadata))
        return g

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        data, index = ICBase._decodeHdf(d)
        return cls(data, index, json.loads(d.attrs[cls.MDTAG]))

    @classmethod
    def getMetadata(cls, directory: str, name: str) -> dict:
        with h5py.File(os.path.join(directory, f'{name}{cls.FILESUFFIX}')) as hf:
            dset = hf[cls.DATASETTAG]
            return json.loads(dset.attr[cls.MDTAG])

    @classmethod
    def validPath(cls, path: str) -> Tuple[bool, Union[str, bytes], Union[str, bytes]]:
        if cls.FILESUFFIX in path:
            directory, fileName = os.path.split(path)
            name = fileName.split(cls.FILESUFFIX)[0]
            with h5py.File(os.path.join(directory, f'{name}{cls.FILESUFFIX}')) as hf:
                valid = cls.MDTAG in hf[cls.DATASETTAG].attrs
            return valid, directory, name
        else:
            return False, '', ''
