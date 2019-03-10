import json
from typing import Tuple

import h5py
import jsonschema
from pandas.tests.io.json import test_json_table_schema

from pwspy.imCube.ICBaseClass import ICBase
import numpy as np
import os


class ExtraReflectanceCube(ICBase):
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'extraReflectionMetadataSchema',
                   'title': 'extraReflectionMetadataSchema',
                   'required': ['system', 'description'],
                   'type': 'object',
                   'properties': {
                       'system': {'type': 'string'},
                       'description': {'type': 'string'}
                        }
                   }

    def __init__(self, data: np.ndarray, wavelengths:Tuple[float, ...], metadata: dict):
        jsonschema.validate(instance=metadata, schema=self._jsonSchema)
        super().__init__(data, wavelengths)
        self.metadata = metadata

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self.index

    @classmethod
    def load(cls, directory: str, name: str):
        with h5py.File(os.path.join(directory, f'{name}_eReflectance.h5')) as hf:
            return cls(hf['data'], hf['wavelengths'], json.loads(hf['metadata']))

    def save(self, directory: str, name: str) -> None:
        savePath = os.path.join(directory, f'{name}_eReflectance.h5')
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            hf.create_dataset('data', data=self.data)
            hf.create_dataset('wavelengths', data=self.wavelengths)
            hf.create_dataset('metadata', np.string_(json.dumps(self.metadata)))
