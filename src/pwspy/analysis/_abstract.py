from __future__ import annotations
from abc import ABC, abstractmethod
import json
import os.path as osp
from typing import List, Optional, Type
import h5py
import numpy as np
import typing
from pwspy import __version__ as pwspyversion
from pwspy.utility.misc import cached_property

if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ICBase


class AbstractAnalysisGroup(ABC):
    #TODO these are pretty much unused. Get rid of them?
    """This class is simply used to group together analysis classes that are compatible with eachother."""
    @staticmethod
    @abstractmethod
    def settingsClass() -> Type[AbstractAnalysisSettings]:
        pass

    @staticmethod
    @abstractmethod
    def resultsClass() -> Type[AbstractAnalysisResults]:
        pass

    @staticmethod
    @abstractmethod
    def analysisClass() -> Type[AbstractAnalysis]:
        pass


class AbstractAnalysisSettings(ABC):
    """This abstract class lays out the basic skeleton of what an AnalysisSettings class should implement."""
    @classmethod
    def fromJson(cls, filePath: str, name: str):
        """Create a new instance of this class from a json text file."""
        with open(osp.join(filePath, f'{name}_{cls.FileSuffix}.json'), 'r') as f:
            d=json.load(f)
        return cls._fromDict(d)

    def toJson(self, filePath: str, name: str):
        """Save this object to a json text file."""
        d = self._asDict()
        with open(osp.join(filePath, f'{name}_{self.FileSuffix}.json'), 'w') as f:
            json.dump(d, f, indent=4)

    def toJsonString(self):
        """Use `_asDict` to convert an instance of this class to a json string"""
        return json.dumps(self._asDict(), indent=4)

    @classmethod
    def fromJsonString(cls, string: str):
        """Use `_fromDict` to load a new instance of the `cls` from a json string."""
        return cls._fromDict(json.loads(string))

    @abstractmethod
    def _asDict(self) -> dict:
        """Implementing class should override this method to return a `dict` with setting names as the keys and the values of the settings as the values."""
        pass

    @classmethod
    @abstractmethod
    def _fromDict(cls, d: dict) -> AbstractAnalysisSettings:
        """Implementing subclass, `cls`, should override this classmethod to return an instance of `cls` based on the `dict`, `d`."""
        pass

    @property
    @abstractmethod
    def FileSuffix(self):
        """Implementing subclass should override this property to return a constant string which will be used as a suffix for json files saving the settings of this class."""
        pass


class AbstractAnalysis(ABC):
    """This abstract class lays out the basic skeleton that an analysis class should implement."""
    @abstractmethod
    def __init__(self, settings: AbstractAnalysisSettings):
        """Does all of the one-time tasks needed to start running an analysis. e.g. prepare the reference, load the extrareflection cube, etc."""
        self.settings = settings

    @abstractmethod
    def run(self, cube: ICBase) -> AbstractAnalysisResults:
        """Given an ImCube to analyze this function returns an instanse of AnalysisResults. In the PWSAnalysisApp this function is run in parallel by the AnalysisManager."""
        pass

    @abstractmethod
    def copySharedDataToSharedMemory(self):
        """When running the `run` method in parallel memory for the object used must be copied to each new process. We can avoid that and save a lot of Ram by moving data
        that is shared between processes to shared memory. If you don't want to implement this then just override it and raise NotImplementedError"""
        pass

class AbstractAnalysisResults(ABC):
    """This abstract class lays out the most basic skeleton of what an AnalysisResults object should implement."""

    _currentmoduleversion = pwspyversion

    @classmethod
    @abstractmethod
    def create(cls):
        """Used to create results from existing variables. These results can then be saved to file."""
        pass

    @classmethod
    @abstractmethod
    def load(cls, directory: str, name: str):
        """Used to load results from a saved file"""
        pass


class AbstractHDFAnalysisResults(AbstractAnalysisResults):
    """This abstract class implements method of `AbstractAnalysisResults` for an object that can be saved and loaded to/from an HDF file. Classes implementing this abstract
    class should implement:  the `fields` property, a list of string names of the datafields that the analysis involves. The `_name2Filename` method which, given an analysis id name,
     returns the file name for the hdf5 file. And the `fileName2Name` method which does the opposite operation."""

    #TODO this holds onto the reference to the h5py.File meaning that the file can't be deleted until the object has been deleted. Maybe that's good. but it causes some problems.
    def __init__(self, file: h5py.File, variablesDict: dict, analysisName: Optional[str] = None):
        """"Can be instantiated with one of the two arguments. To load from file provide the h5py file. To create from variable provide a dictionary keyed by all the field names.
        This initializer should not be run directly, it should only be used by the `create` and `load` class methods."""
        if file is not None:
            assert variablesDict is None
        elif variablesDict is not None:
            assert file is None
        self.file = file
        self.dict = variablesDict
        self.analysisName = analysisName

    @cached_property
    def moduleVersion(self) -> str:
        """Return the version of pwspy that this file was saved with."""
        return bytes(np.array(self.file['pwspy_version'])).decode()

    @staticmethod
    @abstractmethod
    def fields() -> List[str]:
        pass

    @staticmethod
    @abstractmethod
    def name2FileName(name: str) -> str:
        pass

    @staticmethod
    @abstractmethod
    def fileName2Name(fileName: str) -> str:
        pass

    def toHDF(self, directory: str, name: str):
        """Save the AnalysisResults object to an HDF file in `directory`. The name of the file will be determined by `name`. If you want to know what the full file name
        will be you can use this class's `_name2FileName` method."""
        from pwspy.dataTypes import ICBase  # Need this for instance checking
        fileName = osp.join(directory, self.name2FileName(name))
        if osp.exists(fileName):
            raise OSError(f'{fileName} already exists.')
        with h5py.File(fileName, 'w') as hf:
            # Save version
            hf.create_dataset('pwspy_version', data=np.string_(self._currentmoduleversion))
            # Save fields defined by implementing subclass
            for field in self.fields():
                k = field
                v = getattr(self, field)
                if isinstance(v, AbstractAnalysisSettings):
                    v = v.toJsonString()
                if isinstance(v, str):
                    hf.create_dataset(k, data=np.string_(v))  # h5py recommends encoding strings this way for compatability.
                elif isinstance(v, ICBase):
                    hf = v.toHdfDataset(hf, k, fixedPointCompression=True)
                elif isinstance(v, np.ndarray):
                    hf.create_dataset(k, data=v)
                elif v is None:
                    pass
                else:
                    raise TypeError(f"Analysis results type {k}, {type(v)} not supported or expected")

    @classmethod
    def load(cls, directory: str, name: str):
        """Load an analyisResults object from an hdf5 file located in `directory`."""
        filePath = osp.join(directory, cls.name2FileName(name))
        if not osp.exists(filePath):
            raise OSError("The analysis file does not exist.")
        file = h5py.File(filePath, 'r')
        return cls(file, None, name)

    def __del__(self):
        if self.file:
            self.file.close()
