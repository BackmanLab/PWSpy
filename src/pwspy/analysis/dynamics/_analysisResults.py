from __future__ import annotations
from datetime import datetime
from typing import Optional

from ._analysisSettings import DynamicsAnalysisSettings
from pwspy.moduleConsts import dateTimeFormat
from pwspy.analysis._abstract import AbstractHDFAnalysisResults
from pwspy.utility.misc import cached_property
import numpy as np
import typing
if typing.TYPE_CHECKING:
    from ...dataTypes import DynCube


def getFromDict(func):
    """This decorator makes it so that the function will only be evaluated if self.file is not None.
    If self.file is None then we will just search self.dict for a value with a key matching the name of the decorated function.
    We use this because while we often want to load data from a file for use, we also want to support the case of an object
    that has been created but has not yet been saved to a file."""
    def newFunc(self, *args):
        if self.file is None:
            return self.dict[func.__name__]
        else:
            return func(self, *args)

    newFunc.__name__ = func.__name__
    return newFunc


class DynamicsAnalysisResults(AbstractHDFAnalysisResults):
    @staticmethod
    def fields():
        return ['meanReflectance', 'reflectance', 'rms_t', 'dSlope', 'time', 'settings', 'imCubeIdTag', 'referenceIdTag', 'extraReflectionIdTag']

    @staticmethod
    def name2FileName(name: str) -> str:
        return f'dynAnalysisResults_{name}.h5'

    @staticmethod
    def fileName2Name(fileName: str) -> str:
        return fileName.split('dynAnalysisResults_')[1][:-3]

    @classmethod
    def create(cls, settings: DynamicsAnalysisSettings, meanReflectance: np.ndarray, rms_t: np.ndarray, reflectance: DynCube, dSlope: np.ndarray,
                imCubeIdTag: str, referenceIdTag: str, extraReflectionIdTag: Optional[str]):
        #TODO check datatypes here
        d = {'time': datetime.now().strftime(dateTimeFormat),
            'meanReflectance': meanReflectance,
            'reflectance': reflectance,
            'dSlope': dSlope,
            'rms_t': rms_t,
            'imCubeIdTag': imCubeIdTag,
            'referenceIdTag': referenceIdTag,
            'extraReflectionIdTag': extraReflectionIdTag,
            'settings': settings}
        return cls(None, d)

    @cached_property
    @getFromDict
    def meanReflectance(self) -> np.ndarray:
        dset = self.file['meanReflectance']
        return np.array(dset)

    @cached_property
    @getFromDict
    def rms_t(self) -> np.ndarray:
        dset = self.file['rms_t']
        return np.array(dset)

    @cached_property
    @getFromDict
    def settings(self) -> DynamicsAnalysisSettings:
        return DynamicsAnalysisSettings.fromJsonString(self.file['settings'])

    @cached_property
    @getFromDict
    def reflectance(self) -> DynCube:
        dset = self.file['reflectance']
        return DynCube.fromHdfDataset(dset)

    @cached_property
    @getFromDict
    def dSlope(self) -> np.ndarray:
        dset = self.file['dSlope']
        return np.array(dset)

    @cached_property
    @getFromDict
    def imCubeIdTag(self) -> str:
        return bytes(np.array(self.file['imCubeIdTag'])).decode()

    @cached_property
    @getFromDict
    def referenceIdTag(self) -> str:
        return bytes(np.array(self.file['referenceIdTag'])).decode()

    @cached_property
    @getFromDict
    def time(self) -> str:
        return self.file['time']

    @cached_property
    @getFromDict
    def extraReflectionIdTag(self) -> str:
        return bytes(np.array(self.file['extraReflectionIdTag'])).decode()
