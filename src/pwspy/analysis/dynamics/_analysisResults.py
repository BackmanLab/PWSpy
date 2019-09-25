from datetime import datetime
from typing import Optional

from analysis.dynamics._analysisSettings import DynamicsAnalysisSettings
from moduleConsts import dateTimeFormat
from pwspy.analysis._abstract import AbstractAnalysisResults
from utility.misc import cached_property
import numpy as np

def getFromDict(func):
    def newFunc(self, *args):
        if self.file is None:
            return self.dict[func.__name__]
        else:
            return func(self, *args)

    newFunc.__name__ = func.__name__
    return newFunc

class DynamicsAnalysisResults(AbstractAnalysisResults):
    @staticmethod
    def fields():
        return ['meanReflectance', 'rms_t', 'time', 'settings', 'imCubeIdTag', 'referenceIdTag', 'extraReflectionIdTag']


    @classmethod
    def create(cls, settings: DynamicsAnalysisSettings, meanReflectance: np.ndarray, rms: np.ndarray,
                imCubeIdTag: str, referenceIdTag: str, extraReflectionIdTag: Optional[str]):
        #TODO check datatypes here
        d = {'time': datetime.now().strftime(dateTimeFormat),
            'meanReflectance': meanReflectance,
            'rms': rms,
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
    def rms(self) -> np.ndarray:
        dset = self.file['rms']
        return np.array(dset)

    @cached_property
    @getFromDict
    def settings(self) -> DynamicsAnalysisSettings:
        return DynamicsAnalysisSettings.fromJsonString(self.file['settings'])

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
    def extraReflectionTag(self) -> str:
        return bytes(np.array(self.file['extraReflectionTag'])).decode()
