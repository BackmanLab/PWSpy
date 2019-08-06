from __future__ import annotations
import dataclasses
from typing import Optional, Tuple

import h5py
import numpy as np
import os.path as osp
from datetime import datetime
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import KCube
from ._analysisSettings import AnalysisSettings
from abc import ABC, abstractmethod
from pwspy.moduleConsts import dateTimeFormat
from pwspy.utility.misc import cached_property


class AbstractAnalysisResults(ABC):
    """Enforce that derived classes will have the following properties."""
    @property
    @abstractmethod
    def settings(self) -> AnalysisSettings:
        pass

    @property
    @abstractmethod
    def reflectance(self) -> KCube:
        pass

    @property
    @abstractmethod
    def meanReflectance(self) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def rms(self) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def polynomialRms(self) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def autoCorrelationSlope(self) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def rSquared(self) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def ld(self) -> np.ndarray:
        pass

    @property
    @abstractmethod
    def opd(self) -> Tuple[np.ndarray, np.ndarray]:
        pass

    @property
    @abstractmethod
    def time(self) -> str:
        pass

    @property
    @abstractmethod
    def imCubeIdTag(self) -> str:
        pass

    @property
    @abstractmethod
    def referenceIdTag(self) -> str:
        pass

    @property
    @abstractmethod
    def extraReflectionTag(self) -> str:
        pass

    @staticmethod
    def name2FileName(name: str) -> str:
        return f'analysisResults_{name}.h5'

    @staticmethod
    def fileName2Name(fileName: str) -> str:
        return fileName.split('analysisResults_')[1][:-3]


@dataclasses.dataclass
class AnalysisResultsSaver: #TODO this should inherit from abstract class but it doesn't work easily
    """A saveable object to hold the results of an analysis. Also stored the creation time of the analysis."""
    settings: AnalysisSettings
    reflectance: KCube
    meanReflectance: np.ndarray
    rms: np.ndarray
    polynomialRms: np.ndarray
    autoCorrelationSlope: np.ndarray
    rSquared: np.ndarray
    ld: np.ndarray
    imCubeIdTag: str
    referenceIdTag: str
    extraReflectionTag: Optional[str]
    time: str = None

    def __post_init__(self):
        self.__setattr__('time', datetime.now().strftime(dateTimeFormat))

    def toHDF5(self, directory: str, name: str):
        from pwspy.dataTypes import KCube #Need this for instance checking
        fileName = osp.join(directory, AbstractAnalysisResults.name2FileName(name))
        if osp.exists(fileName):
            raise OSError(f'{fileName} already exists.')
        # now save the stuff
        with h5py.File(fileName, 'w') as hf:
            for k, v in self.__dict__.items():
                if k == 'settings':
                    v = v.toJsonString()
                if isinstance(v, str):
                    hf.create_dataset(k, data=np.string_(v))  # h5py recommends encoding strings this way for compatability.
                elif isinstance(v, KCube):
                    hf = v.toFixedPointHdfDataset(hf, k)
                elif isinstance(v, np.ndarray):
                    hf.create_dataset(k, data=v)
                elif v is None:
                    pass  # Don't bother writing values that were skipped.
                else:
                    raise TypeError(f"Analysis results type {k}, {type(v)} not supported or expected")


def clearError(func):
    def newFunc(*args):
        try:
            return func(*args)
        except KeyError:
            raise KeyError(f"The analysis file does not contain a {func.__name__} item.")
    newFunc.__name__ = func.__name__  # failing to do this renaming can mess with other decorators e.g. cached_property
    return newFunc

class AnalysisResultsLoader(AbstractAnalysisResults): #TODO All these cached properties stay in memory once they are loaded. It may be necessary to add a mechanism to decache them when memory is needed.
    """A read-only loader for analysis results that will only load them from hard disk as needed."""
    def __init__(self, directory: str, name: str):
        self.filePath = osp.join(directory, self.name2FileName(name))
        self.analysisName = name
        self.file = None
        if not osp.exists(self.filePath):
            raise OSError("The analysis file does not exist.")
        self.file = h5py.File(self.filePath, 'r')

    def __del__(self):
        if self.file:
            self.file.close()

    @cached_property
    @clearError
    def settings(self) -> AnalysisSettings:
        return AnalysisSettings.fromJsonString(self.file['settings'])

    @cached_property
    @clearError
    def imCubeIdTag(self) -> str:
        return bytes(np.array(self.file['imCubeIdTag'])).decode()

    @cached_property
    @clearError
    def referenceIdTag(self) -> str:
        return bytes(np.array(self.file['referenceIdTag'])).decode()

    @cached_property
    @clearError
    def time(self) -> str:
        return self.file['time']

    @cached_property
    @clearError
    def reflectance(self):
        from pwspy.dataTypes import KCube
        dset = self.file['reflectance']
        return KCube.fromHdfDataset(dset)

    @cached_property
    @clearError
    def meanReflectance(self) -> np.ndarray:
        dset = self.file['meanReflectance']
        return np.array(dset)

    @cached_property
    @clearError
    def rms(self) -> np.ndarray:
        dset = self.file['rms']
        return np.array(dset)

    @cached_property
    @clearError
    def polynomialRms(self) -> np.ndarray:
        dset = self.file['polynomialRms']
        return np.array(dset)

    @cached_property
    @clearError
    def autoCorrelationSlope(self) -> np.ndarray:
        dset = self.file['autoCorrelationSlope']
        return np.array(dset)

    @cached_property
    @clearError
    def rSquared(self) -> np.ndarray:
        dset = self.file['rSquared']
        return np.array(dset)

    @cached_property
    @clearError
    def ld(self) -> np.ndarray:
        dset = self.file['ld']
        return np.array(dset)

    @cached_property
    @clearError
    def opd(self) -> Tuple[np.ndarray, np.ndarray]:
        from pwspy.dataTypes import KCube
        dset = self.file['reflectance']
        cube = KCube.fromHdfDataset(dset)
        opd, opdIndex = cube.getOpd(isHannWindow=True, indexOpdStop=100)
        return opd, opdIndex

    @cached_property
    @clearError
    def extraReflectionTag(self) -> str:
        return bytes(np.array(self.file['extraReflectionTag'])).decode()

    # def loadAllFromDisk(self) -> None:
    #     """Access all cached properties in order to load them from disk"""
    #     for i in [self.opdIndex, self.opd, self.ld, self.rSquared,
    #               self.autoCorrelationSlope, self.polynomialRms,
    #               self.rms, self.reflectance, self.time, self.referenceIdTag,
    #               self.imCubeIdTag, self.settings, self.extraReflectionTag]:
    #         try:
    #             _ = i
    #         except KeyError:
    #             print(f"Skipping nonexistent `{i.__name__}` field.")

