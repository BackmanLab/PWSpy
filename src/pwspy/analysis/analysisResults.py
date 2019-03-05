from dataclasses import dataclass
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

    def __post_init__(self):
        self.__setattr__('time', datetime.now().strftime("%m-%d-%y %H:%M:%s"))

    def toHDF5(self, directory: str, name: str):
        fileName = osp.join(directory, f'{name}.hdf5')
        if osp.exists(fileName):
            raise OSError(f'{fileName} already exists.')
        #now save the stuff

    @classmethod
    def load(cls, directory: str, name: str):
        fileName = osp.join(directory, f'{name}.hdf5')
        #load stuff