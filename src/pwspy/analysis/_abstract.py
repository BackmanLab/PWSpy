from __future__ import annotations
from abc import ABC, abstractmethod
import json
import os.path as osp

from dataTypes._ICBaseClass import ICBase


class AbstractAnalysisSettings(ABC):

    @classmethod
    def fromJson(cls, filePath: str, name: str):
        with open(osp.join(filePath, f'{name}_{cls.FileSuffix}.json'), 'r') as f:
            d=json.load(f)
        return cls._fromDict(d)

    def toJson(self, filePath: str, name: str):
        d = self._asDict()
        with open(osp.join(filePath, f'{name}_{self.FileSuffix}.json'), 'w') as f:
            json.dump(d, f, indent=4)

    def toJsonString(self):
        return json.dumps(self._asDict(), indent=4)

    @classmethod
    def fromJsonString(cls, string: str):
        return cls._fromDict(json.loads(string))

    @abstractmethod
    def _asDict(self) -> dict:
       pass

    @classmethod
    @abstractmethod
    def _fromDict(cls, d: dict) -> AbstractAnalysisSettings:
        pass

    @property
    @abstractmethod
    def FileSuffix(self):
        pass


class AbstractAnalysis(ABC):
    @abstractmethod
    def __init__(self, settings: AbstractAnalysisSettings):
        """Does all of the one-time tasks needed to start running an analysis. e.g. prepare the reference, load the extrareflection cube, etc."""
        self.settings = settings

    @abstractmethod
    def run(self, cube: ICBase) -> AbstractAnalysisResults:
        """Given an ImCube to analyze this function returns an instanse of AnalysisResultsSaver. In the PWSAnalysisApp this function is run in parallel by the AnalysisManager."""
        pass

class AbstractAnalysisResults(ABC):
    pass