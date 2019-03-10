import json
from typing import Tuple

import h5py
from pandas.tests.io.json import test_json_table_schema

from pwspy.imCube.ICBaseClass import ICBase
import numpy as np
import os

class ExtraReflectionCube(ICBase):
    def __init__(self, data: np.ndarray, wavelengths:Tuple[float, ...], metadata: dict):
        self._checkMetadata(metadata)
        super().__init__(data, wavelengths)
        self.metadata = metadata

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self.index

    @classmethod
    def load(cls, directory: str, name: str):


    def save(self, directory: str, name: str) -> None:
        savePath = os.path.join(directory, f'.h5')
        if os.path.exists(savePath):
            raise OSError(f"The path {savePath} already exists.")
        with h5py.File(savePath, 'w') as hf:
            hf.create_dataset('data', data=self.data)
            hf.create_dataset('wavelengths', data=self.wavelengths)
            hf.create_dataset('metadata', np.string_(json.dumps(self.metadata)))

    def _checkMetadata(self, md: dict) -> None:
        