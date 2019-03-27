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
                   'required': ['system', 'description', 'time'],
                   'type': 'object',
                   'properties': {
                       'system': {'type': 'string'},
                       'description': {'type': 'string'},
                       'time': {'type': 'string'}
                        }
                   }
    _fileSuffix = '_eReflectance.h5'
    _dataSetTag = 'extraReflection'
    _mdTag = 'metadata'

    def __init__(self, data: np.ndarray, wavelengths: Tuple[float, ...], metadata: dict):
        jsonschema.validate(instance=metadata, schema=self._jsonSchema)
        if data.max() > 1 or data.min() < 0:
            raise ValueError("Reflectance values must be between 0 and 1")
        datetime.strftime(metadata['time'], dateTimeFormat)  # Make sure that the time can be parsed.
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
        with h5py.File(os.path.join(directory, f'{name}{cls._fileSuffix}')) as hf:
            dset = hf[cls._dataSetTag]
            return cls.fromHdfDataset(dset)

    def toHdfFile(self, directory: str, name: str) -> None:
        savePath = os.path.join(directory, f'{name}{self._fileSuffix}')
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            self.toHdfDataset(hf, name)

    def toHdfDataset(self, g: h5py.Group, name: str) -> h5py.Group:
        g = super().toHdfDataset(g, self._dataSetTag)
        g.attrs[self._mdTag] = np.string_(json.dumps(self.metadata))
        return g

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset):
        data, index = ICBase._decodeHdf(d)
        return cls(data, index, json.loads(d.attrs[cls._mdTag]))

    @classmethod
    def getMetadata(cls, directory: str, name: str) -> dict:
        with h5py.File(os.path.join(directory, f'{name}{cls._fileSuffix}')) as hf:
            dset = hf[cls._dataSetTag]
            return json.loads(dset.attr[cls._mdTag])

    @classmethod
    def validPath(cls, path: str) -> Tuple[bool, Union[str, bytes], Union[str, bytes]]:
        if cls._fileSuffix in path:
            directory, fileName = os.path.split(path)
            name = fileName.split(cls._fileSuffix)[0]
            with h5py.File(os.path.join(directory, f'{name}{cls._fileSuffix}')) as hf:
                try:
                    valid = cls._mdTag in hf[cls._dataSetTag].attrs
                except:
                    valid = False
            return valid, directory, name
        else:
            return False, '', ''
