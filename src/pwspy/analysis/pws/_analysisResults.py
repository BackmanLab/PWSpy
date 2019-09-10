from __future__ import annotations
from typing import Optional, Tuple
import h5py
import numpy as np
import os.path as osp
from datetime import datetime
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import KCube
from analysis.pws._analysisSettings import AnalysisSettings
from pwspy.moduleConsts import dateTimeFormat
from pwspy.utility.misc import cached_property
from pwspy.analysis._abstract import AbstractAnalysisResults


def clearError(func):
    def newFunc(*args):
        try:
            return func(*args)
        except KeyError:
            raise KeyError(f"The analysis file does not contain a {func.__name__} item.")
    newFunc.__name__ = func.__name__  # failing to do this renaming can mess with other decorators e.g. cached_property
    return newFunc

def getFromDict(func):
    def newFunc(self, *args):
        if self.file is None:
            return self.dict[func.__name__]
        else:
            return func(self, *args)
    newFunc.__name__ = func.__name__
    return newFunc


class PWSAnalysisResults(AbstractAnalysisResults): #TODO All these cached properties stay in memory once they are loaded. It may be necessary to add a mechanism to decache them when memory is needed.
    """A read-only loader for analysis results that will only load them from hard disk as needed."""
    fields = ['time', 'reflectance', 'meanReflectance', 'rms', 'polynomialRms', 'autoCorrelationSlope', 'rSquared',
                'ld', 'imCubeIdTag', 'referenceIdTag', 'extraReflectionTag', 'settings']

    def __init__(self, file: h5py.File, variablesDict: dict):
        if file is not None:
            assert variablesDict is None
        elif variablesDict is not None:
            assert file is None
        self.file = file
        self.dict = variablesDict

    @staticmethod
    def name2FileName(name: str) -> str:
        return f'analysisResults_{name}.h5'

    @staticmethod
    def fileName2Name(fileName: str) -> str:
        return fileName.split('analysisResults_')[1][:-3]


    @classmethod
    def fromHDF(cls, directory: str, name: str):
        filePath = osp.join(directory, cls.name2FileName(name))
        if not osp.exists(filePath):
            raise OSError("The analysis file does not exist.")
        file = h5py.File(filePath, 'r')
        return cls(file, None)

    @classmethod
    def create(cls, settings: AnalysisSettings, reflectance: KCube, meanReflectance: np.ndarray, rms: np.ndarray,
                polynomialRms: np.ndarray, autoCorrelationSlope: np.ndarray, rSquared: np.ndarray, ld: np.ndarray,
                imCubeIdTag: str, referenceIdTag: str, extraReflectionTag: Optional[str]):
        #TODO check datatypes here
        d = {'time': datetime.now().strftime(dateTimeFormat),
            'reflectance': reflectance,
            'meanReflectance': meanReflectance,
            'rms': rms,
            'polynomialRms': polynomialRms,
            'autoCorrelationSlope': autoCorrelationSlope,
            'rSquared': rSquared,
            'ld': ld,
            'imCubeIdTag': imCubeIdTag,
            'referenceIdTag': referenceIdTag,
            'extraReflectionTag': extraReflectionTag,
            'settings': settings}
        return cls(None, d)

    def toHDF(self, directory: str, name: str):
        from pwspy.dataTypes import KCube #Need this for instance checking
        fileName = osp.join(directory, self.name2FileName(name))
        if osp.exists(fileName):
            raise OSError(f'{fileName} already exists.')
        # now save the stuff
        with h5py.File(fileName, 'w') as hf:
            for field in self.fields:
                k = field
                v = getattr(self, field)
                if k == 'settings':
                    v = v.toJsonString()

                if isinstance(v, str):
                    hf.create_dataset(k, data=np.string_(v))  # h5py recommends encoding strings this way for compatability.
                elif isinstance(v, KCube):
                    hf = v.toFixedPointHdfDataset(hf, k)
                elif isinstance(v, np.ndarray):
                    hf.create_dataset(k, data=v)
                elif v is None:
                    pass
                else:
                    raise TypeError(f"Analysis results type {k}, {type(v)} not supported or expected")

    @cached_property
    @clearError
    @getFromDict
    def settings(self) -> AnalysisSettings:
        return AnalysisSettings.fromJsonString(self.file['settings'])

    def __del__(self):
        if self.file:
            self.file.close()

    @cached_property
    @clearError
    @getFromDict
    def imCubeIdTag(self) -> str:
        return bytes(np.array(self.file['imCubeIdTag'])).decode()

    @cached_property
    @clearError
    @getFromDict
    def referenceIdTag(self) -> str:
        return bytes(np.array(self.file['referenceIdTag'])).decode()

    @cached_property
    @clearError
    @getFromDict
    def time(self) -> str:
        return self.file['time']

    @cached_property
    @clearError
    @getFromDict
    def reflectance(self):
        from pwspy.dataTypes import KCube
        dset = self.file['reflectance']
        return KCube.fromHdfDataset(dset)

    @cached_property
    @clearError
    @getFromDict
    def meanReflectance(self) -> np.ndarray:
        dset = self.file['meanReflectance']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def rms(self) -> np.ndarray:
        dset = self.file['rms']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def polynomialRms(self) -> np.ndarray:
        dset = self.file['polynomialRms']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def autoCorrelationSlope(self) -> np.ndarray:
        dset = self.file['autoCorrelationSlope']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def rSquared(self) -> np.ndarray:
        dset = self.file['rSquared']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def ld(self) -> np.ndarray:
        dset = self.file['ld']
        return np.array(dset)

    @cached_property
    @clearError
    @getFromDict
    def opd(self) -> Tuple[np.ndarray, np.ndarray]:
        from pwspy.dataTypes import KCube
        dset = self.file['reflectance']
        cube = KCube.fromHdfDataset(dset)
        opd, opdIndex = cube.getOpd(isHannWindow=True, indexOpdStop=100)
        return opd, opdIndex

    @cached_property
    @clearError
    @getFromDict
    def extraReflectionTag(self) -> str:
        return bytes(np.array(self.file['extraReflectionTag'])).decode()
