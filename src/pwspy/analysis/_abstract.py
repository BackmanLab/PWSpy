# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import annotations
from abc import ABC, abstractmethod
import json
import os.path as osp
import h5py
import numpy as np
import typing
from pwspy import __version__ as pwspyversion
from pwspy.utility.misc import cached_property
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ICBase


class AbstractAnalysisSettings(ABC):
    """This abstract class lays out the basic skeleton of what an AnalysisSettings class should implement.
    These classes represent everything about the settings of an anlysis that can be reliably saved and then loaded again.
    The settings that are actually passed to the analyiss are the RuntimeSettings which can contain items that can't reliably be
    loaded from a json file (for example, references to data files which may not still be at the same file path if someone tried to load the settings"""

    @classmethod
    def fromJson(cls, filePath: str, name: str) -> AbstractAnalysisSettings:
        """Create a new instance of this class from a json text file.

        Args:
            filePath: The path to the folder containing the JSON file to be loaded.
            name: The name that the analysis was saved as.
        Returns:
            A new instance of an analysis settings class.
        """
        with open(osp.join(filePath, f'{name}_{cls.FileSuffix}.json'), 'r') as f:
            d = json.load(f)
        return cls._fromDict(d)

    def toJson(self, filePath: str, name: str):
        """Save this object to a json text file.

        Args:
            filePath: The path to the folder to contain the new JSON file.
            name: The name to save the analysis as.
        """
        d = self._asDict()
        with open(osp.join(filePath, f'{name}_{self.FileSuffix}.json'), 'w') as f:
            json.dump(d, f, indent=4)

    def toJsonString(self) -> str:
        """Use `_asDict` to convert an instance of this class to a json string.

        Returns:
            A JSON formatted string.
        """
        return json.dumps(self._asDict(), indent=4)

    @classmethod
    def fromJsonString(cls, string: str) -> AbstractAnalysisSettings:
        """Use `_fromDict` to load a new instance of the `cls` from a json string.

        Args:
            string: A JSON formatted string to load the object from.
        Returns:
            A new instance of analysis settings class.
        """
        return cls._fromDict(json.loads(string))

    @abstractmethod
    def _asDict(self) -> dict:
        """

         Returns:
            A dictionary with setting names as the keys and the values of the settings as the values.
        """
        pass

    @classmethod
    @abstractmethod
    def _fromDict(cls, d: dict) -> AbstractAnalysisSettings:
        """
        Args:
            d: A dictionary containing analysis settings.
        Returns:
            A new instance of the analysis settings class based on `d`."""
        pass

    @property
    @abstractmethod
    def FileSuffix(self):
        """A constant string which will be used as a suffix for json files saving the settings of this class."""
        pass


class AbstractAnalysis(ABC):
    """This abstract class lays out the basic skeleton that an analysis class should implement."""
    @abstractmethod
    def __init__(self):
        """Does all of the one-time tasks needed to start running an analysis. e.g. prepare the reference, load the extrareflection cube, etc."""
        pass

    @abstractmethod
    def run(self, cube: ICBase) -> AbstractAnalysisResults:
        """Given an data cube to analyze this function returns an instanse of AnalysisResults. In the PWSAnalysisApp this function is run in parallel by the AnalysisManager.

        Args:
            cube: A data cube to be analyzed using the settings provided in the constructor of this class.
        Returns:
            A new instance of analysis results.
        """
        pass

    @abstractmethod
    def copySharedDataToSharedMemory(self):
        """When running the `run` method in parallel memory for the object used must be copied to each new process. We can avoid that and save a lot of Ram by moving data
        that is shared between processes to shared memory. If you don't want to implement this then just override it and raise NotImplementedError"""
        pass


class AbstractAnalysisResults(ABC):
    """This abstract class lays out the most basic skeleton of what an AnalysisResults object should implement."""

    _currentmoduleversion = pwspyversion  # We save the version of this code that was used to save the results. For retrospection

    @classmethod
    @abstractmethod
    def create(cls) -> AbstractAnalysisResults:
        """Used to create results from existing variables. These results can then be saved to file.

        Returns:
            A new instance of analysis results.
        """
        pass

    @classmethod
    @abstractmethod
    def load(cls, directory: str, name: str):
        """Used to load results from a saved file.

        Args:
            directory: The path to the folder containing the analysis file.
            name: The name that the analysis was saved as.
        Returns:
            A new instance of analysis results loaded from file.
        """
        pass


def _clearError(func):
    """This decorator tries to run the original function. If the function raises a keyerror then we raise a new keyerror with a clearer message. This is intended to be used with `field` accessors of implementations
    of `AbstractHDFAnalysisResults`."""
    def newFunc(*args):
        try:
            return func(*args)
        except KeyError:
            raise KeyError(f"The analysis file does not contain a {func.__name__} item.")
    newFunc.__name__ = func.__name__  # failing to do this renaming can mess with other decorators e.g. cached_property
    return newFunc


def _getFromDict(func):
    """This decorator makes it so that when the method is run we will check if our class instance has a `file` property. If not, then we will attempt to access a `dict` property which is keyed
    by the same name as our original method. Otherwide we simply run the method. This is intended for use with implementations of `AbstractHDFAnalysisResults`"""
    def newFunc(self, *args):
        if self.file is None:
            return self.dict[func.__name__]
        else:
            return func(self, *args)

    newFunc.__name__ = func.__name__
    return newFunc


class AbstractHDFAnalysisResults(AbstractAnalysisResults):
    """
    This abstract class implements methods of `AbstractAnalysisResults` for an object that can be saved and loaded to/from an HDF file.
    And the `fileName2Name` method which does the opposite operation. Can be instantiated with one of the two constructor arguments.
    The constructor should not be run directly, it should only be used by the `create` and `load` class methods.

    Args:
        file: To load from file provide the `h5py.File`.
        variablesDict: To create a new object from variables, provide a dictionary keyed by all the field names.
        analysisName: Optionally store the name of the analysis.
    """
    @staticmethod
    def FieldDecorator(func):
        """Decorate functions in subclasses that access their fields from the HDF file with this decorator. It will:
        1: Make it so the data is load from disk on the first access and stored in memory for every further access.
        2: Report an understandable error if the field isn't found in the HDF file.
        3: Make the accessors work even if the the object isn't associated with an HDF file."""
        return cached_property(_clearError(_getFromDict(func)))

    #TODO this holds onto the reference to the h5py.File meaning that the file can't be deleted until the object has been deleted. Maybe that's good. but it causes some problems.
    def __init__(self, file: typing.Optional[h5py.File] = None, variablesDict: typing.Optional[dict] = None, analysisName: typing.Optional[str] = None):
        if file is not None:
            assert variablesDict is None
        elif variablesDict is not None:
            assert file is None
        self.file = file
        self.dict = variablesDict
        self.analysisName = analysisName

    @cached_property
    def moduleVersion(self) -> str:
        """The version of PWSpy code that this file was saved with."""
        return bytes(np.array(self.file['pwspy_version'])).decode()

    @staticmethod
    @abstractmethod
    def fields() -> typing.Tuple[str, ...]:
        """

        Returns:
            A sequence of string names of the datafields that the analysis results contains.
        """
        pass

    @staticmethod
    @abstractmethod
    def name2FileName(name: str) -> str:
        """

        Args:
            name: An analysis name.
        Returns:
            The corresponding file name for the hdf5 file.
        """
        pass

    @staticmethod
    @abstractmethod
    def fileName2Name(fileName: str) -> str:
        """

        Args:
            fileName: The filename that the HDF file was saved as.

        Returns:
            The analysis name.
        """
        pass

    def toHDF(self, directory: str, name: str, overwrite: bool = False, compression: str = None):
        """
        Save the AnalysisResults object to an HDF file in `directory`. The name of the file will be determined by `name`. If you want to know what the full file name
        will be you can use this class's `name2FileName` method.

        Args:
            directory: The path to the folder to save the file in.
            name: The name of the analysis. This determines the file name.
            overwrite: If `True` then any existing file of the same name will be replaced.
            compression: The value of this argument will be passed to h5py.create_dataset for numpy arrays. See h5py documentation for available options.
        """
        from pwspy.dataTypes import ICBase  # Need this for instance checking
        fileName = osp.join(directory, self.name2FileName(name))
        if (not overwrite) and osp.exists(fileName):
            raise OSError(f'{fileName} already exists.')
        with open(fileName, 'wb') as pythonFile:
            with h5py.File(pythonFile, 'w', driver='fileobj') as hf:  # Using the default driver causes write errors when writing from windows to a Samba shared server. Using a reference to a python `File Object` solves this issue.
                # Save version
                hf.create_dataset('pwspy_version', data=np.string_(self._currentmoduleversion))
                # Save fields defined by implementing subclass
                for field in self.fields():
                    k = field
                    v = getattr(self, field)
                    if isinstance(v, AbstractAnalysisSettings):
                        v = v.toJsonString() # Convert to string, then string case will then handle saving the string.
                    elif isinstance(v, dict):  # Save as json. The str case will handle the actual saving.
                        v = json.dumps(v)
                    if isinstance(v, str):
                        hf.create_dataset(k, data=np.string_(v))  # h5py recommends encoding strings this way for compatability.
                    elif isinstance(v, ICBase):
                        hf = v.toHdfDataset(hf, k, fixedPointCompression=True)
                    elif isinstance(v, np.ndarray):
                        hf.create_dataset(k, data=v, compression=compression)
                    elif v is None:
                        pass
                    else:
                        raise TypeError(f"Analysis results type {k}, {type(v)} not supported or expected")

    @classmethod
    def load(cls, directory: str, name: str) -> AbstractHDFAnalysisResults:
        """Load an analyis results object from an HDF5 file located in `directory`.

        Args:
            directory: The path to the folder containing the file.
            name: The name of the analysis.
        Returns:
            A new instance of analysis results loaded from file.
        """
        filePath = osp.join(directory, cls.name2FileName(name))
        if not osp.exists(filePath):
            raise OSError(f"The {cls.__name__} analysis file does not exist. {filePath}")
        file = h5py.File(filePath, 'r')
        return cls(file, None, name)

    def __del__(self):
        if self.file is not None:  # Make sure to release the file if it's still open.
            try:
                self.file.close()
            except:  # Sometimes when python is shutting down this causes an error. Doesn't matter though.
                pass

