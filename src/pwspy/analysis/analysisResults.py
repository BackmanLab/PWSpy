from dataclasses import dataclass

import h5py
import numpy as np
import os.path as osp
from datetime import datetime
from .analysisSettings import AnalysisSettings


@dataclass(frozen=True)
class AnalysisResults:
    settings: AnalysisSettings
    reflectance: np.ndarray
    rms: np.ndarray
    polynomialRms: np.ndarray
    autoCorrelationSlope: np.ndarray
    rSquared: np.ndarray
    ld: np.ndarray
    opd: np.ndarray
    xvalOpd: np.ndarray
    time: str = None

    def __post_init__(self):
        self.__setattr__('time', datetime.now().strftime("%m-%d-%y %H:%M:%s"))

    def toHDF5(self, directory: str, name: str):
        fileName = osp.join(directory, f'{name}.hdf5')
        if osp.exists(fileName):
            raise OSError(f'{fileName} already exists.')
        # now save the stuff
        with h5py.File(fileName, 'w') as hf:
            for k,v in self.asdict().items():
                hf.create_dataset(k, data=v)

    @classmethod
    def fromHDF5(cls, directory: str, name: str):
        fileName = osp.join(directory, f'{name}.hdf5')
        # load stuff
        with h5py.File(fileName, 'r') as hf:
            d = {k: np.array(v) for k,v in hf.items()}
            return cls(**d)
