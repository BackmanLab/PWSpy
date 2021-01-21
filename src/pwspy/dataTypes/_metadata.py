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
import json
import logging
import multiprocessing as mp
import os
import pathlib
import subprocess
import sys
import typing
import abc
from datetime import datetime
import enum
from typing import Optional, Tuple, Union, List
import h5py
import jsonschema
import numpy as np
import tifffile as tf
from scipy import io as spio
from pwspy.analysis import AbstractHDFAnalysisResults
from pwspy.dataTypes import _jsonSchemasPath
from pwspy.dataTypes._other import CameraCorrection, Roi
import pwspy.dataTypes._data as pwsdtd
from pwspy import dateTimeFormat
from pwspy.utility.misc import cached_property


class MetaDataBase(abc.ABC):
    """
    This base class provides that basic functionality to store information about a PWS related acquisition on file.

    Args:
        metadata: A dictionary containing the metadata
        filePath: The path to the location the metadata was loaded from
        acquisitionDirectory: A reference to the `AcqDir` associated with this object.

    """

    @property
    @abc.abstractmethod
    def _jsonSchemaPath(self) -> str:
        """Each sublass should provide a path to the jsonschema file. this is needed in order to resolve jsonschema references"""
        pass

    @property
    @abc.abstractmethod
    def _jsonSchema(self) -> dict:
        """Each subclass should provide a json schema loaded from a file.
        This serves as a schematic that can be checked against when loading metadata to make sure it contains the required information."""
        pass

    def __init__(self, metadata: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        logger = logging.getLogger(__name__)
        self.filePath = filePath
        self.acquisitionDirectory = acquisitionDirectory
        refResolver = jsonschema.RefResolver(pathlib.Path(self._jsonSchemaPath).as_uri(), None)  # This resolver is used to allow derived json schemas to refer to the base schema.
        jsonschema.validate(instance=metadata, schema=self._jsonSchema, types={'array': (list, tuple)}, resolver=refResolver)
        self.dict: dict = metadata
        try:
            datetime.strptime(self.dict['time'], dateTimeFormat)
        except ValueError:
            try:
                logger.info("Detected a non-compliant timestamp. attempting to correct.")
                self.dict['time'] = datetime.strftime(datetime.strptime(self.dict['time'], "%d-%m-%y %H:%M:%S"), dateTimeFormat)
            except ValueError:
                logger.warning("The time stamp could not be parsed. Replacing with 1_1_1970")
                self.dict['time'] = "1-1-1990 01:01:01"
        if self.dict['system'] == "":
            logger.warning("The `system` name in the metadata is blank. Check that the PWS System is saving the proper calibration values.")
        if all([i in self.dict for i in ['darkCounts', 'linearityPoly']]):
            if self.dict['darkCounts'] == 0:
                logger.warning("Detected a darkCounts value of 0 in the pwsdtd.ImCube Metadata. Check that the PWS System is saving the proper calibration values.")
            self.cameraCorrection = CameraCorrection(darkCounts=self.dict['darkCounts'],
                                                     linearityPolynomial=self.dict['linearityPoly'])
        else:
            self.cameraCorrection = None

    @abc.abstractmethod
    def toDataClass(self, lock: typing.Optional[mp.Lock]) -> pwsdtd.ICBase:
        """Convert the metadata class to a class that loads the data

        Args:
            lock: A `Lock` object used to synchronize IO in multithreaded and multiprocessing applications.
        """
        pass

    @abc.abstractmethod
    def idTag(self) -> str:
        """A string that uniquely identifies this data."""
        pass

    @property
    def binning(self) -> int:
        """
        The binning setting used by the camera. This is needed in order to properly correct dark counts.
        This is generally extracted from metadata saved by Micromanager
        """
        return self.dict['binning']

    @property
    def pixelSizeUm(self) -> float:
        """
        The pixelSize expressed in microns. This represents the length of each square pixel in object space. Binning
        has already been accounted for here. This is generally extracted from metadata saved my MicroManager
        """
        return self.dict['pixelSizeUm']

    @property
    def exposure(self) -> float:
        """The exposure time of the camera expressed in milliseconds."""
        return self.dict['exposure']

    @property
    def time(self) -> str:
        """The date and time that the acquisition was taken."""
        return self.dict['time']

    @property
    def systemName(self) -> str:
        """The name of the system this was acquired on. The name is set in the `PWS Acquisition Plugin` for Micromanager."""
        return self.dict['system']

    @staticmethod
    def decodeHdfMetadata(d: h5py.Dataset) -> dict:
        """Attempt to extract a dictionary of metadata from an HDF5 dataset.

        Args:
            d: The `h5py.Dataset` to load from.
        Returns:
            A dictionary containing the metadata
        """
        assert 'metadata' in d.attrs
        return json.loads(d.attrs['metadata'])

    def encodeHdfMetadata(self, d: h5py.Dataset) -> h5py.Dataset:
        """Save this metadata object as a json string in an HDF5 dataset.

        Args:
            d: The `h5py.Dataset` to save the metadata to.
        """
        d.attrs['metadata'] = np.string_(json.dumps(self.dict))
        return d


class AnalysisManager(abc.ABC):
    """Handles the functionality to save, load, etc. analysis files.

    Args:
        metadata: A dictionary containing the metadata
        filePath: The path to the location the metadata was loaded from
        acquisitionDirectory: A reference to the `AcqDir` associated with this object.

    """
    def __init__(self, filePath: str):
        self.__filePath = filePath

    @staticmethod
    @abc.abstractmethod
    def getAnalysisResultsClass() -> typing.Type[AbstractHDFAnalysisResults]:
        """

        Returns:
            AbstractHDFAnalysisResults: The class that contains analysis results for this acquisition type
        """
        pass

    def getAnalyses(self) -> typing.List[str]:
        """

        Returns:
            A list of the names of analyses that were found.
        """
        assert self.__filePath is not None
        return self.getAnalysesAtPath(self.__filePath)

    @classmethod
    def getAnalysesAtPath(cls, path: str) -> typing.List[str]:
        """

        Args:
            path: The path to search for analysis files.

        Returns:
            A list of the names of analyses that were found.
        """
        anPath = os.path.join(path, 'analyses')
        if os.path.exists(anPath):
            files = os.listdir(os.path.join(path, 'analyses'))
            return [cls.getAnalysisResultsClass().fileName2Name(f) for f in files]
        else:
            return []

    def saveAnalysis(self, analysis: AbstractHDFAnalysisResults, name: str):
        """

        Args:
            analysis: An AnalysisResults object to be saved.
            name: The name to save the analysis as
        """
        path = os.path.join(self.__filePath, 'analyses')
        if not os.path.exists(path):
            os.mkdir(path)
        analysis.toHDF(path, name)

    def loadAnalysis(self, name: str) -> AbstractHDFAnalysisResults:
        """

        Args:
            name: The name of the analysis to load.

        Returns:
            A new instance of an AnalysisResults object.
        """
        return self.getAnalysisResultsClass().load(os.path.join(self.__filePath, 'analyses'), name)

    def removeAnalysis(self, name: str):
        """

        Args:
            name: The name of the analysis to be deleted
        """
        os.remove(os.path.join(self.__filePath, 'analyses', self.getAnalysisResultsClass().name2FileName(name)))


class DynMetaData(MetaDataBase, AnalysisManager):
    """A class that represents the metadata of a Dynamics acquisition."""
    class FileFormats(enum.Enum):
        """An enumerator identifying the types of file formats that this class can be loaded from."""
        Tiff = enum.auto()
        RawBinary = enum.auto()
        Hdf = enum.auto()

    @staticmethod
    def getAnalysisResultsClass() -> typing.Type[AbstractHDFAnalysisResults]:
        from pwspy.analysis.dynamics import DynamicsAnalysisResults
        return DynamicsAnalysisResults

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'DynMetaData.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, metadata: dict, filePath: Optional[str] = None, fileFormat: Optional[FileFormats] = None, acquisitionDirectory: Optional[AcqDir] = None):
        self.fileFormat = fileFormat
        MetaDataBase.__init__(self, metadata, filePath, acquisitionDirectory=acquisitionDirectory)
        AnalysisManager.__init__(self, filePath)

    def toDataClass(self, lock: mp.Lock = None) -> pwsdtd.DynCube:
        """
        Args:
            lock (mp.Lock): A multiprocessing `lock` that can prevent help us synchronize demands on the hard drive when loading many files in parallel. Probably not needed.
        Returns:
            pwsdtmd.DynCube: The data object associated with this metadata object.
        """
        # from pwspy.dataTypes.data import DynCube
        return pwsdtd.DynCube.fromMetadata(self, lock)

    @property
    def idTag(self) -> str:
        """

        Returns:
            str: A unique string identifying this acquisition.
        """
        return f"DynCube_{self.dict['system']}_{self.dict['time']}"

    @property
    def wavelength(self) -> int:
        """The wavelength that this acquisition was acquired at."""
        return self.dict['wavelength']

    @property
    def times(self) -> Tuple[float, ...]:
        """A sequence indicatin the time associated with each 2D slice of the 3rd axis of the `data` array"""
        return self.dict['times']

    @classmethod
    def fromOldPWS(cls, directory: str, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> DynMetaData:
        """Loads old dynamics cubes which were saved the same as old pws cubes. a raw binary file with some metadata saved in random .mat files. Does not support
        automatic detection of binning, pixel size, camera dark counts, system name.

        Args:
            directory: The path to the folder containing the data files load the metadata from.

        Returns:
            A new instance of `DynMetaData`.
        """
        if lock is not None:
            lock.acquire()
        try:
            #While the info2 file exists for old dynamics acquisitions, it is just garbage char.
            info3 = list(spio.loadmat(os.path.join(directory, 'info3.mat'))['info3'].squeeze())
            wv = list(spio.loadmat(os.path.join(directory, 'WV.mat'))['WV'].squeeze())
            wv = [int(i) for i in wv]  # We will have issues saving later if these are numpy int types.
            assert all([i == wv[0] for i in wv]), "The wavelengths of the dynamics cube are not all identical."
            md = {
                #RequiredMetadata
                'exposure': info3[1],
                'time': '{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(
                    *[int(i) for i in [info3[8], info3[7], info3[6], info3[9], info3[10], info3[11]]]),
                'system': str(info3[0]),
                'binning': None,
                'pixelSizeUm': None,
                'wavelength': wv[0],
                'times': [i*info3[1] for i in range(len(wv))],  # We don't have any record of the times so we just have to assume it matches exactly with the exposure time, this is in milliseconds.
                #Extra metadata
                'systemId': info3[0],
                'imgHeight': int(info3[2]), 'imgWidth': int(info3[3]), 'wavelengths': wv
                }
        finally:
            if lock is not None:
                lock.release()
        return cls(md, filePath=directory, fileFormat=DynMetaData.FileFormats.RawBinary, acquisitionDirectory=acquisitionDirectory)

    @classmethod
    def fromTiff(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> DynMetaData:
        """

        Args:
            directory: The path to the folder containing the data files load the metadata from.
        Returns:
            A new instance of `DynMetaData` loaded from file.
        """
        if lock is not None:
            lock.acquire()
        try:
            if os.path.exists(os.path.join(directory, 'dyn.tif')):
                path = os.path.join(directory, 'dyn.tif')
            else:
                raise OSError("No Tiff file was found at:", directory)
            if os.path.exists(os.path.join(directory, 'dynmetadata.json')):
                metadata = json.load(open(os.path.join(directory, 'dynmetadata.json'), 'r'))
            else:
                with tf.TiffFile(path) as tif:
                    metadata = json.loads(tif.imagej_metadata['Info'])  # The micromanager plugin saves metadata as the info property of the imagej imageplus object.
        finally:
            if lock is not None:
                lock.release()
        metadata['binning'] = metadata['MicroManagerMetadata']['Binning']['scalar']  # Get binning from the micromanager metadata
        metadata['pixelSizeUm'] = metadata['MicroManagerMetadata']['PixelSizeUm']['scalar']  # Get the pixel size from the micromanager metadata
        if metadata['pixelSizeUm'] == 0: metadata['pixelSizeUm'] = None
        return cls(metadata, filePath=directory, fileFormat=cls.FileFormats.Tiff, acquisitionDirectory=acquisitionDirectory)

    def getThumbnail(self) -> np.ndarray:
        """Return the image used for quick viewing of the acquisition. Has no numeric significance."""
        with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
            return f.asarray()


class ERMetaData:
    """A class representing the extra information related to an ExtraReflectanceCube file. This can be useful as a object
    to keep track of a ExtraReflectanceCube without having to have the data from the file loaded into memory.

    Args:
        inheritedMetadata: The metadata dictionary will often just be inherited information from one of the `ImCubes` that was used to create
            this ER Cube. While this data can be useful it should be taken with a grain of salt. E.G. the metadata will contain
            an `exposure` field. In reality this ER Cube will have been created from pwsdtd.ImCubes at a variety of exposures.
        numericalAperture: The numerical aperture that the ImCubes used to generate this Extra reflection cube were imaged at.
        filePath: The path to the file that this object is stored in.
    """
    _jsonSchema = {"$schema": "http://json-schema.org/schema#",
                   '$id': 'extraReflectionMetadataSchema',
                   'title': 'extraReflectionMetadataSchema',
                   'required': ['system', 'time', 'wavelengths', 'pixelSizeUm', 'binning', 'numericalAperture'],
                   'type': 'object',
                   'properties': {
                       'system': {'type': 'string'},
                       'time': {'type': 'string'},
                       'wavelengths': {'type': 'array',
                                        'items': {'type': 'number'}
                                        },
                       'pixelSizeUm': {'type': ['number', 'null']},
                       'binning': {'type': ['integer', 'null']},
                       'numericalAperture': {'type': ['number']}
                        }
                   }
    FILESUFFIX = '_eReflectance.h5'
    DATASETTAG = 'extraReflection'
    _MDTAG = 'metadata'

    def __init__(self, inheritedMetadata: dict, numericalAperture: float, filePath: str=None):
        self.inheritedMetadata = inheritedMetadata
        self.inheritedMetadata['numericalAperture'] = numericalAperture
        jsonschema.validate(instance=inheritedMetadata, schema=self._jsonSchema, types={'array': (list, tuple)})
        self.filePath = filePath

    @property
    def idTag(self) -> str:
        """A unique tag to identify this acquisition by."""
        return f"ExtraReflection_{self.inheritedMetadata['system']}_{self.inheritedMetadata['time']}"

    @property
    def numericalAperture(self) -> float:
        """The numerical aperture that this cube was imaged at."""
        return self.inheritedMetadata['numericalAperture']

    @property
    def systemName(self) -> str:
        """The name of the system that this image was acquired on."""
        return self.inheritedMetadata['system']

    @classmethod
    def validPath(cls, path: str) -> Tuple[bool, Union[str, bytes], Union[str, bytes]]:
        """

        Args:
            path: The file path to the file to search for valid ExtraReflectance files.

        Returns:
            A tuple containing: validPath: True if the path is valid, directory: The directory the file is in, name: The name that the object was saved as.
        """
        if cls.FILESUFFIX in path:
            directory, name = cls.directory2dirName(path)
            with h5py.File(os.path.join(directory, f'{name}{cls.FILESUFFIX}'), 'r') as hf:
                valid = cls._MDTAG in hf[cls.DATASETTAG].attrs
            return valid, directory, name
        else:
            return False, '', ''

    @classmethod
    def fromHdfFile(cls, directory: str, name: str) -> ERMetaData:
        """

        Args:
            directory: The directory the file is saved in.
            name: The name the object was saved as.

        Returns:
            A new instance of `ERMetaData` object
        """
        filePath = cls.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[cls.DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None) -> ERMetaData:
        """

        Args:
            d: The `h5py.Dataset` to load the object from.

        Returns:
            A new instance of `ERMetaData` object
        """
        mdDict = json.loads(d.attrs[cls._MDTAG])
        return cls(mdDict, mdDict['numericalAperture'], filePath=filePath)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        """

        Args:
            g: The `h5py.Group` to save the new dataset into.

        """
        g[self.DATASETTAG].attrs[self._MDTAG] = np.string_(json.dumps(self.inheritedMetadata))
        return g

    @classmethod
    def directory2dirName(cls, path: str) -> Tuple[Union[bytes, str], Union[bytes, str]]:
        """

        Args:
            path: The path to the file that stores an `ExtraReflectanceCube` object.

        Returns:
            A tuple containing: directory: The directory path, name: The name that the file was saved as.
        """
        directory, fileName = os.path.split(path)
        if not fileName.endswith(cls.FILESUFFIX):
            raise ValueError(f"The file name \"{fileName}\" is not recognized as a {cls.__name__} file. Should end with \"{cls.FILESUFFIX}\".")
        name = fileName.split(cls.FILESUFFIX)[0]
        return directory, name

    @classmethod
    def dirName2Directory(cls, directory: str, name: str) -> str:
        """
        This is the inverse of `directory2dirName`
        """
        return os.path.join(directory, f'{name}{cls.FILESUFFIX}')


class FluorMetaData(MetaDataBase):
    """
    Metadata for a fluorescence image.

    Args:
        md: A dictionary containing the metadata

    """
    FILENAME = 'fluor.tif'
    MDPATH = 'fluorMetadata.json'

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'MetaDataBase.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, md: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        super().__init__(md, filePath, acquisitionDirectory)

    def toDataClass(self, lock: mp.Lock = None) -> pwsdtd.FluorescenceImage:
        return pwsdtd.FluorescenceImage.fromMetadata(self, lock)

    @property
    def idTag(self):
        return f"Fluor_{self.dict['system']}_{self.dict['time']}"

    @classmethod
    def fromTiff(cls, directory: str, acquisitionDirectory: Optional[AcqDir]) -> FluorMetaData:
        """Load from a TIFF file.

        Args:
            directory: The path to the folder to load from.

        Returns:
            A new instance of `FluorMetaData` loaded from file.
        """
        if not FluorMetaData.isValidPath(directory):
            raise ValueError(f"Fluorescence image not found in {directory}.")
        with open(os.path.join(directory, FluorMetaData.MDPATH), 'r') as f:
            dic = json.load(f)

        # Get binning from the micromanager metadata
        binning = dic['MicroManagerMetadata']['Binning']['scalar']
        dic['binning'] = binning
        # Get the pixel size from the micromanager metadata
        try:
            dic['pixelSizeUm'] = dic['MicroManagerMetadata']['PixelSizeUm']['scalar']
        except KeyError:
            dic['pixelSizeUm'] = None
        if dic['pixelSizeUm'] == 0: dic['pixelSizeUm'] = None

        return FluorMetaData(dic, directory, acquisitionDirectory)

    @classmethod
    def isValidPath(cls, directory: str):
        """

        Args:
            directory: The path to search for valid files.

        Returns:
            True if a valid file was found.
        """
        path = os.path.join(directory, cls.FILENAME)
        path2 = os.path.join(directory, cls.MDPATH)
        return os.path.exists(path) and os.path.exists(path2)

    def getThumbnail(self) -> np.ndarray:
        """

        Returns:
            An image for quick viewing of the acquisition. No numerical significance.
        """
        with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
            return f.asarray()


class ICMetaData(MetaDataBase, AnalysisManager):
    """A class that represents the metadata of a PWS acquisition.

    Args:
        metadata: The dictionary containing the metadata.
    """
    class FileFormats(enum.Enum):
        RawBinary = enum.auto()
        Tiff = enum.auto()
        Hdf = enum.auto()
        NanoMat = enum.auto()

    @staticmethod
    def getAnalysisResultsClass() -> typing.Type[AbstractHDFAnalysisResults]:
        from pwspy.analysis.pws import PWSAnalysisResults
        return PWSAnalysisResults

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'ICMetaData.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, metadata: dict, filePath: Optional[str] = None, fileFormat: ICMetaData.FileFormats = None, acquisitionDirectory: Optional[AcqDir] = None):
        MetaDataBase.__init__(self, metadata, filePath, acquisitionDirectory=acquisitionDirectory)
        AnalysisManager.__init__(self, filePath)
        self.fileFormat: ICMetaData.FileFormats = fileFormat
        self.dict['wavelengths'] = tuple(np.array(self.dict['wavelengths']).astype(float))

    def toDataClass(self, lock: mp.Lock = None) -> pwsdtd.ImCube:
        return pwsdtd.ImCube.fromMetadata(self, lock)

    @cached_property
    def idTag(self) -> str:
        return f"ImCube_{self.dict['system']}_{self.dict['time']}"

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self.dict['wavelengths']

    @classmethod
    def loadAny(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> ICMetaData:
        """
        Attempt to load from any file format.

        Args:
            directory: The file path to load the metadata from.
        Returns:
            A new instance of `ICMetaData` loaded from file
        """
        try:
            return ICMetaData.fromTiff(directory, lock=lock, acquisitionDirectory=acquisitionDirectory)
        except:
            try:
                return ICMetaData.fromOldPWS(directory, lock=lock, acquisitionDirectory=acquisitionDirectory)
            except:
                try:
                    return ICMetaData.fromNano(directory, lock=lock, acquisitionDirectory=acquisitionDirectory)
                except:
                    raise OSError(f"Could not find a valid PWS image cube file at {directory}.")

    @classmethod
    def fromOldPWS(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> ICMetaData:
        """
        Attempt to load from the old .mat file format.

        Args:
            directory: The file path to load the metadata from.
        Returns:
            A new instance of `ICMetaData` loaded from file
        """
        if lock is not None:
            lock.acquire()
        try:
            try:
                md = json.load(open(os.path.join(directory, 'pwsmetadata.txt')))
            except:  # have to use the old metadata
                info2 = list(spio.loadmat(os.path.join(directory, 'info2.mat'))['info2'].squeeze())
                info3 = list(spio.loadmat(os.path.join(directory, 'info3.mat'))['info3'].squeeze())
                logging.getLogger(__name__).info("Json metadata not found. Using backup metadata.")
                wv = list(spio.loadmat(os.path.join(directory, 'WV.mat'))['WV'].squeeze())
                wv = [int(i) for i in wv]  # We will have issues saving later if these are numpy int types.
                md = {'startWv': info2[0], 'stepWv': info2[1], 'stopWv': info2[2],
                      'exposure': info2[3], 'time': '{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(
                        *[int(i) for i in [info3[8], info3[7], info3[6], info3[9], info3[10], info3[11]]]),
                      'systemId': info3[0], 'system': str(info3[0]),
                      'imgHeight': int(info3[2]), 'imgWidth': int(info3[3]), 'wavelengths': wv,
                      'binning': None, 'pixelSizeUm': None}
        finally:
            if lock is not None:
                lock.release()
        return cls(md, filePath=directory, fileFormat=ICMetaData.FileFormats.RawBinary, acquisitionDirectory=acquisitionDirectory)

    @classmethod
    def fromNano(cls, directory: str, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> ICMetaData:
        """
        Attempt to load from NanoCytomic .mat file format

        Args:
            directory: The file path to load the metadata from.
        Returns:
            A new instance of `ICMetaData` loaded from file
        """
        if lock is not None:
            lock.acquire()
        try:
            with h5py.File(os.path.join(directory, 'imageCube.mat'), 'r') as hf:
                cubeParams = hf['cubeParameters']
                lam = cubeParams['lambda']
                exp = cubeParams['exposure'] #we don't support adaptive exposure.
                md = {'startWv': lam['start'][0, 0], 'stepWv': lam['step'][0, 0], 'stopWv': lam['stop'][0, 0],
                      'exposure': exp['base'][0, 0], 'time': datetime.strptime(np.string_(cubeParams['metadata']['date'][()].astype(np.uint8)).decode(), '%Y%m%dT%H%M%S').strftime(dateTimeFormat),
                      'system': np.string_(cubeParams['metadata']['hardware']['system']['id'][()].astype(np.uint8)).decode(), 'wavelengths': list(lam['sequence'][0]),
                      'binning': None, 'pixelSizeUm': None}
        finally:
            if lock is not None:
                lock.release()
        return cls(md, filePath=directory, fileFormat=ICMetaData.FileFormats.NanoMat, acquisitionDirectory=acquisitionDirectory)

    @classmethod
    def fromTiff(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> ICMetaData:
        """
        Attempt to load from the standard TIFF file format.

        Args:
            directory: The file path to load the metadata from.
        Returns:
            A new instance of `ICMetaData` loaded from file
        """
        if lock is not None:
            lock.acquire()
        try:
            if os.path.exists(os.path.join(directory, 'MMStack.ome.tif')):
                path = os.path.join(directory, 'MMStack.ome.tif')
            elif os.path.exists(os.path.join(directory, 'pws.tif')):
                path = os.path.join(directory, 'pws.tif')
            else:
                raise OSError("No Tiff file was found at:", directory)
            if os.path.exists(os.path.join(directory, 'pwsmetadata.json')):
                metadata = json.load(open(os.path.join(directory, 'pwsmetadata.json'), 'r'))
            else:
                with tf.TiffFile(path) as tif:
                    try:
                        metadata = json.loads(tif.pages[0].description)
                    except:
                        metadata = json.loads(tif.imagej_metadata['Info'])  # The micromanager plugin saves metadata as the info property of the imagej imageplus object.
                    metadata['time'] = tif.pages[0].tags['DateTime'].value
        finally:
            if lock is not None:
                lock.release()
        #For a while the micromanager metadata was getting saved weird this fixes it.
        if 'major_version' in metadata['MicroManagerMetadata']:
            metadata['MicroManagerMetadata'] = metadata['MicroManagerMetadata']['map']
        # Get binning from the micromanager metadata
        binning = metadata['MicroManagerMetadata']['Binning']
        if isinstance(binning, dict):  # This is due to a property map change from beta to gamma
            binning = binning['scalar']
        metadata['binning'] = binning
        # Get the pixel size from the micromanager metadata
        try:
            metadata['pixelSizeUm'] = metadata['MicroManagerMetadata']['PixelSizeUm']['scalar']
        except KeyError:
            metadata['pixelSizeUm'] = None
        if metadata['pixelSizeUm'] == 0: metadata['pixelSizeUm'] = None
        if 'waveLengths' in metadata:  # Fix an old naming issue
            metadata['wavelengths'] = metadata['waveLengths']
            del metadata['waveLengths']
        return cls(metadata, filePath=directory, fileFormat=ICMetaData.FileFormats.Tiff, acquisitionDirectory=acquisitionDirectory)

    def metadataToJson(self, directory):
        """
        Save the metadata to a JSON file.

        Args:
            directory: The folder path to save the new file to.

        """
        with open(os.path.join(directory, 'pwsmetadata.json'), 'w') as f:
            json.dump(self.dict, f)

    def getThumbnail(self) -> np.ndarray:
        """

        Returns:
            An image for quick viewing of the acquisition. No numerical significance.
        """
        if self.fileFormat == ICMetaData.FileFormats.NanoMat:
            with h5py.File(os.path.join(self.filePath, 'image_bd.mat'), 'r') as hf:
                return np.array(hf['image_bd']).T.copy()  # For some reason these are saved transposed?
        else:
            with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
                return f.asarray()


class AcqDir:
    """This class handles the file structure of a single acquisition. this can include a PWS acquisition as well as colocalized Dynamics and fluorescence.

    Args:
        directory: the file path the root directory of the acquisition
    """
    def __init__(self, directory: str):
        self.filePath = directory #TODO should this be forced to an absolute path? Doesn't appear to be causing any problems like it is now.
        if (self.pws is None) and (self.dynamics is None) and (len(self.fluorescence) == 0):
            raise OSError(f"Could not find a valid PWS or Dynamics Acquisition at {directory}.")

    def __repr__(self):
        return f"AcqDir({self.filePath})"

    @cached_property
    def pws(self) -> Optional[ICMetaData]:
        """ICMetaData: Returns None if no PWS acquisition was found."""
        try:
            return ICMetaData.loadAny(os.path.join(self.filePath, 'PWS'), acquisitionDirectory=self)
        except:
            try:
                return ICMetaData.loadAny(os.path.join(self.filePath), acquisitionDirectory=self) #Many of the old files are saved here in the root directory.
            except:
                return None

    @cached_property
    def dynamics(self) -> Optional[DynMetaData]:
        """DynMetaData: Returns None if no dynamics acquisition was found."""
        try:
            return DynMetaData.fromTiff(os.path.join(self.filePath, 'Dynamics'), acquisitionDirectory=self)
        except:
            try:
                return DynMetaData.fromOldPWS(self.filePath, acquisitionDirectory=self) #This is just for old acquisitions where they were saved in their own folder that was indistinguishable from a PWS acquisitison.
            except:
                return None

    @cached_property
    def fluorescence(self) -> typing.List[FluorMetaData]:
        # Newer acquisitions allow for multiple fluorescence images saved to numbered subfolders
        i = 0
        imgs = []
        while True:
            path = os.path.join(self.filePath, f"Fluorescence_{i}")
            if not os.path.exists(path):
                break
            try:
                imgs.append(FluorMetaData.fromTiff(path, acquisitionDirectory=self))
            except ValueError:
                logging.getLogger(__name__).info(f"Failed to load fluorescence metadata at {path}")
            i += 1
        if len(imgs) == 0:  # No files were found.
            # Old files only had a single fluorescence image with no number on the folder name.
            path = os.path.join(self.filePath, 'Fluorescence')
            if os.path.exists(path):
                return [FluorMetaData.fromTiff(path, acquisitionDirectory=self)]
            else:
                return []
        else:
            return imgs

    @property
    def idTag(self):
        if self.pws is not None:
            return self.pws.idTag
        else: #We must have one of these two items.
            return self.dynamics.idTag

    def getRois(self) -> List[Tuple[str, int, Roi.FileFormats]]:
        """Return information about the Rois found in the acquisition's file path.
        See documentation for Roi.getValidRoisInPath()"""
        assert self.filePath is not None
        return Roi.getValidRoisInPath(self.filePath)

    def loadRoi(self, name: str, num: int, fformat: Roi.FileFormats = None) -> Roi:
        """Load a Roi that has been saved to file in the acquisition's file path."""
        assert isinstance(name, str)
        assert isinstance(num, int)
        if fformat == Roi.FileFormats.MAT:
            return Roi.fromMat(self.filePath, name, num)
        elif fformat == Roi.FileFormats.HDF2:
            return Roi.fromHDF(self.filePath, name, num)
        elif fformat == Roi.FileFormats.HDF:
            return Roi.fromHDF_legacy(self.filePath, name, num)
        else:
            return Roi.loadAny(self.filePath, name, num)

    def saveRoi(self, roi: Roi, overwrite: bool = False) -> None:
        """Save a Roi to file in the acquisition's file path."""
        roi.toHDF(self.filePath, overwrite=overwrite)

    def deleteRoi(self, name: str, num: int):
        Roi.deleteRoi(self.filePath, name, num)

    def editNotes(self):
        """Create a `notes.txt` file if it doesn't already exists and open it in a text editor."""
        filepath = os.path.join(self.filePath, 'notes.txt')
        filepath = os.path.normpath(filepath)  # Sometime there can be an error if we don't clean the file path like this.
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                pass
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name == 'nt':  # For Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # For Linux, Mac, etc.
            subprocess.call(('xdg-open', filepath))

    def hasNotes(self) -> bool:
        """Indicates whether or not a `notes.txt` file was found."""
        return os.path.exists(os.path.join(self.filePath, 'notes.txt'))

    def getNotes(self) -> str:
        """Return the contents of `notes.txt` as a string."""
        if self.hasNotes():
            with open(os.path.join(self.filePath, 'notes.txt'), 'r') as f:
                return '\n'.join(f.readlines())
        else:
            return ''

    def getThumbnail(self) -> np.ndarray:
        """Return a thumbnail from any of the available acquisitions. Should be an 8bit normalized image."""
        if self.pws is not None:
            return self.pws.getThumbnail()
        elif self.dynamics is not None:
            return self.dynamics.getThumbnail()
        elif len(self.fluorescence) != 0:
            return self.fluorescence[0].getThumbnail()

    def getNumber(self) -> int:
        return int(self.filePath.split("Cell")[-1])

    

if __name__ == '__main__':
    md = ICMetaData.fromNano(r'C:\Users\nicke\Desktop\LTL20b_Tracking cells in 50%EtOH,95%EtOH,Water\95% ethanol\Cell1')