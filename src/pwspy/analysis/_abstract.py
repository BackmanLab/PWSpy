from __future__ import annotations
from abc import ABC, abstractmethod
import json
import os.path as osp
from typing import List

from dataTypes._ICBaseClass import ICBase
import h5py
import numpy as np

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
        """Given an ImCube to analyze this function returns an instanse of AnalysisResults. In the PWSAnalysisApp this function is run in parallel by the AnalysisManager."""
        pass

class AbstractAnalysisResults(ABC):
    def __init__(self, file: h5py.File, variablesDict: dict):
        if file is not None:
            assert variablesDict is None
        elif variablesDict is not None:
            assert file is None
        self.file = file
        self.dict = variablesDict

    @classmethod
    @abstractmethod
    def create(cls):
        pass

    @staticmethod
    @abstractmethod
    def name2FileName(name: str) -> str:
        pass

    @staticmethod
    @abstractmethod
    def fileName2Name(fileName: str) -> str:
        pass

    @staticmethod
    @abstractmethod
    def fields() -> List[str]:
        pass

    def toHDF(self, directory: str, name: str):
        from pwspy.dataTypes import KCube #Need this for instance checking
        fileName = osp.join(directory, self.name2FileName(name))
        if osp.exists(fileName):
            raise OSError(f'{fileName} already exists.')
        # now save the stuff
        with h5py.File(fileName, 'w') as hf:
            for field in self.fields():
                k = field
                v = getattr(self, field)
                if isinstance(v, AbstractAnalysisSettings):
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

    @classmethod
    def fromHDF(cls, directory: str, name: str):
        filePath = osp.join(directory, cls.name2FileName(name))
        if not osp.exists(filePath):
            raise OSError("The analysis file does not exist.")
        file = h5py.File(filePath, 'r')
        return cls(file, None)

    def __del__(self):
        if self.file:
            self.file.close()
