from __future__ import annotations
import json
import multiprocessing as mp
import os
import pathlib
import typing
import abc
from datetime import datetime
import enum
from typing import Optional, Tuple, Union
import h5py
import jsonschema
import numpy as np
import tifffile as tf
from scipy import io as spio

from pwspy.analysis._abstract import AbstractHDFAnalysisResults
from pwspy.analysis.dynamics import DynamicsAnalysisResults
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.dataTypes import _jsonSchemasPath, AcqDir, DynCube, FluorescenceImage, ImCube, \
    CameraCorrection, ICBase
from pwspy.moduleConsts import dateTimeFormat
from pwspy.utility.misc import cached_property


class MetaDataBase(abc.ABC):
    """This base class provides that basic functionality to store information about a PWS related acquisition on file."""
    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'MetaDataBase.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)  # This serves as a schematic that can be checked against when loading metadata to make sure it contains the required information.

    def __init__(self, metadata: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        self.filePath = filePath
        if acquisitionDirectory is None:
            if filePath is not None:
                from pwspy.dataTypes import AcqDir
                self.acquisitionDirectory = AcqDir(filePath)  # If we weren't provided with an acquisition directory but we did geta  file path, then assume that the filepath is the same as the directory.
        else:
            self.acquisitionDirectory = acquisitionDirectory
        refResolver = jsonschema.RefResolver(pathlib.Path(self._jsonSchemaPath).as_uri(), None)  # This resolver is used to allow derived json schemas to refer to the base schema.
        jsonschema.validate(instance=metadata, schema=self._jsonSchema, types={'array': (list, tuple)}, resolver=refResolver)
        self._dict: dict = metadata
        try:
            datetime.strptime(self._dict['time'], dateTimeFormat)
        except ValueError:
            try:
                print("Detected a non-compliant timestamp. attempting to correct.")
                self._dict['time'] = datetime.strftime(datetime.strptime(self._dict['time'], "%d-%m-%y %H:%M:%S"), dateTimeFormat)
            except ValueError:
                print("Warning!: The time stamp could not be parsed. Replacing with 1_1_1970")
                self._dict['time'] = "1-1-1990 01:01:01"
        if self._dict['system'] == "":
            print("Warning: The `system` name in the metadata is blank. Check that the PWS System is saving the proper calibration values.")
        if all([i in self._dict for i in ['darkCounts', 'linearityPoly']]):
            if self._dict['darkCounts'] == 0:
                print("Warning: Detected a darkCounts value of 0 in the ImCube Metadata. Check that the PWS System is saving the proper calibration values.")
            self.cameraCorrection = CameraCorrection(darkCounts=self._dict['darkCounts'],
                                                     linearityPolynomial=self._dict['linearityPoly'])
        else:
            self.cameraCorrection = None

    @abc.abstractmethod
    def toDataClass(self, lock: mp.Lock) -> ICBase:
        """Convert the metadata class to a class that loads the data"""
        pass

    @abc.abstractmethod
    def idTag(self) -> str:
        """Return a string that uniquely identifies this data."""
        pass

    @property
    def binning(self) -> int:
        """The binning setting used by the camera. This is needed in order to properly correct dark counts.
        This is generally extracted from metadata saved by Micromanager"""
        return self._dict['binning']

    @property
    def pixelSizeUm(self) -> float:
        """The pixelSize expressed in microns. This represents the length of each square pixel in object space. Binning
        has already been accounted for here. This is generally extracted from metadata saved my MicroManager"""
        return self._dict['pixelSizeUm']

    @property
    def exposure(self) -> float:
        """The exposure time of the camera expressed in milliseconds."""
        return self._dict['exposure']

    @property
    def time(self) -> str:
        """The date and time that the acquisition was taken."""
        return self._dict['time']

    @property
    def systemName(self) -> str:
        """The name of the system this was acquired on. The name is set in the `PWS Acquisition Plugin` for Micromanager."""
        return self._dict['system']

    @staticmethod
    def decodeHdfMetadata(d: h5py.Dataset) -> dict:
        """Attempt to extract a dictionary of metadata from an HDF5 dataset."""
        assert 'metadata' in d.attrs
        return json.loads(d.attrs['metadata'])

    def encodeHdfMetadata(self, d: h5py.Dataset) -> h5py.Dataset:
        """Save this metadata object as a json string in an HDF5 dataset."""
        d.attrs['metadata'] = np.string_(json.dumps(self._dict))
        return d


class AnalysisManagerMetaDataBase(MetaDataBase):
    """Implements the functionality to save, load, etc. analysis files."""
    def __init__(self, metadata: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        super().__init__(metadata, filePath, acquisitionDirectory)

    @staticmethod
    @abc.abstractmethod
    def getAnalysisResultsClass() -> AbstractHDFAnalysisResults:
        """

        Returns:
            AbstractHDFAnalysisResults: The class that contains analysis results for this acquisition type
        """
        pass

    def getAnalyses(self) -> typing.List[str]:
        assert self.filePath is not None
        return self.getAnalysesAtPath(self.filePath)

    @classmethod
    def getAnalysesAtPath(cls, path: str) -> typing.List[str]:
        anPath = os.path.join(path, 'analyses')
        if os.path.exists(anPath):
            files = os.listdir(os.path.join(path, 'analyses'))
            return [cls.getAnalysisResultsClass().fileName2Name(f) for f in files]
        else:
            # print(f"ImCube at {path} has no `analyses` folder.")
            return []

    def saveAnalysis(self, analysis: AbstractHDFAnalysisResults, name: str):
        path = os.path.join(self.filePath, 'analyses')
        if not os.path.exists(path):
            os.mkdir(path)
        analysis.toHDF(path, name)

    def loadAnalysis(self, name: str) -> AbstractHDFAnalysisResults:
        return self.getAnalysisResultsClass().load(os.path.join(self.filePath, 'analyses'), name)

    def removeAnalysis(self, name: str):
        os.remove(os.path.join(self.filePath, 'analyses', self.getAnalysisResultsClass().name2FileName(name)))


class DynMetaData(AnalysisManagerMetaDataBase):
    """A class that represents the metadata of a Dynamics Acquisition."""
    class FileFormats(enum.Enum):
        """An enumerator identifying the types of file formats that this class can be loaded from."""
        Tiff = auto()
        RawBinary = auto()
        Hdf = auto()

    @staticmethod
    def getAnalysisResultsClass(): return DynamicsAnalysisResults

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'DynMetaData.json')
    with open(_jsonSchemaPath) as _f:
        _jsonSchema = json.load(_f)

    def __init__(self, metadata: dict, filePath: Optional[str] = None, fileFormat: Optional[FileFormats] = None, acquisitionDirectory: Optional[AcqDir] = None):
        self.fileFormat = fileFormat
        super().__init__(metadata, filePath, acquisitionDirectory=acquisitionDirectory)

    def toDataClass(self, lock: mp.Lock = None) -> DynCube:
        """
        Args:
            lock (mp.Lock): A multiprocessing `lock` that can prevent help us synchronize demands on the hard drive when loading many files in parallel. Probably not needed.
        Returns:
            DynCube: The data object associated with this metadata object.
        """
        from pwspy.dataTypes import DynCube
        return DynCube.fromMetadata(self, lock)

    @property
    def idTag(self) -> str:
        """

        Returns:
            str: A unique string identifying this acquisition.
        """
        return f"DynCube_{self._dict['system']}_{self._dict['time']}"

    @property
    def wavelength(self) -> int:
        return self._dict['wavelength']

    @property
    def times(self) -> Tuple[float, ...]:
        return self._dict['times']

    @classmethod
    def fromOldPWS(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> DynMetaData:
        """Loads old dynamics cubes which were saved the same as old pws cubes. a raw binary file with some metadata saved in random .mat files. Does not support
        automatic detection of binning, pixel size, camera dark counts, system name."""
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
    def fromTiff(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None):
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
        with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
            return f.asarray()


class ERMetaData:
    """A class representing the extra information related to an ExtraReflectanceCube file. This can be useful as a object
     to keep track of a ExtraReflectanceCube without having to have the data from the file loaded into memory."""
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
    _FILESUFFIX = '_eReflectance.h5'
    _DATASETTAG = 'extraReflection'
    _MDTAG = 'metadata'

    def __init__(self, inheritedMetadata: dict, numericalAperture: float, filePath: str=None):
        """The metadata dictionary will often just be inherited information from one of the ImCubes that was used to create
        this ER Cube. While this data can be useful it should be taken with a grain of salt. E.G. the metadata will contain
        an `exposure` field. In reality this ER Cube will have been created from ImCubes at a variety of exposures."""
        self.inheritedMetadata = inheritedMetadata
        self.inheritedMetadata['numericalAperture'] = numericalAperture
        jsonschema.validate(instance=inheritedMetadata, schema=self._jsonSchema, types={'array': (list, tuple)})
        self.filePath = filePath

    @property
    def idTag(self):
        return f"ExtraReflection_{self.inheritedMetadata['system']}_{self.inheritedMetadata['time']}"

    @property
    def numericalAperture(self):
        return self.inheritedMetadata['numericalAperture']

    @property
    def systemName(self) -> str:
        return self.inheritedMetadata['system']

    @classmethod
    def validPath(cls, path: str) -> Tuple[bool, Union[str, bytes], Union[str, bytes]]:
        if cls._FILESUFFIX in path:
            directory, name = cls.directory2dirName(path)
            with h5py.File(os.path.join(directory, f'{name}{cls._FILESUFFIX}'), 'r') as hf:
                valid = cls._MDTAG in hf[cls._DATASETTAG].attrs
            return valid, directory, name
        else:
            return False, '', ''

    @classmethod
    def fromHdfFile(cls, directory: str, name: str):
        filePath = cls.dirName2Directory(directory, name)
        with h5py.File(filePath, 'r') as hf:
            dset = hf[cls._DATASETTAG]
            return cls.fromHdfDataset(dset, filePath=filePath)

    @classmethod
    def fromHdfDataset(cls, d: h5py.Dataset, filePath: str = None):
        mdDict = json.loads(d.attrs[cls._MDTAG])
        return cls(mdDict, mdDict['numericalAperture'], filePath=filePath)

    def toHdfDataset(self, g: h5py.Group) -> h5py.Group:
        g[self._DATASETTAG].attrs[self._MDTAG] = np.string_(json.dumps(self.inheritedMetadata))
        return g

    @classmethod
    def directory2dirName(cls, path: str) -> Tuple[Union[bytes, str], Union[bytes, str]]:
        directory, fileName = os.path.split(path)
        name = fileName.split(cls._FILESUFFIX)[0]
        return directory, name

    @classmethod
    def dirName2Directory(cls, directory: str, name: str):
        return os.path.join(directory, f'{name}{cls._FILESUFFIX}')


class FluorMetaData(MetaDataBase):
    FILENAME = 'fluor.tif'
    MDPATH = 'fluorMetadata.json'

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'MetaDataBase.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, md: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        super().__init__(md, filePath, acquisitionDirectory)

    def toDataClass(self, lock: mp.Lock = None) -> FluorescenceImage:
        from pwspy.dataTypes import FluorescenceImage
        return FluorescenceImage.fromMetadata(self, lock)

    @property
    def idTag(self):
        return f"Fluor_{self._dict['system']}_{self._dict['time']}"

    @classmethod
    def fromTiff(cls, directory: str, acquisitionDirectory: Optional[AcqDir]):
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

    @staticmethod
    def isValidPath(directory: str):
        path = os.path.join(directory, FluorMetaData.FILENAME)
        path2 = os.path.join(directory, FluorMetaData.MDPATH)
        return os.path.exists(path) and os.path.exists(path2)

    def getThumbnail(self) -> np.ndarray:
        with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
            return f.asarray()


class ICMetaData(AnalysisManagerMetaDataBase):
    class FileFormats(enum.Enum):
        RawBinary = enum.auto()
        Tiff = enum.auto()
        Hdf = enum.auto()
        NanoMat = enum.auto()

    @staticmethod
    def getAnalysisResultsClass(): return PWSAnalysisResults

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'ICMetaData.json')
    with open(_jsonSchemaPath) as _f:
        _jsonSchema = json.load(_f)

    def __init__(self, metadata: dict, filePath: Optional[str] = None, fileFormat: ICMetaData.FileFormats = None, acquisitionDirectory: Optional[AcqDir] = None):
        super().__init__(metadata, filePath, acquisitionDirectory=acquisitionDirectory)
        self.fileFormat: ICMetaData.FileFormats = fileFormat
        self._dict['wavelengths'] = tuple(np.array(self._dict['wavelengths']).astype(float))

    def toDataClass(self, lock: mp.Lock = None) -> ImCube:
        from pwspy.dataTypes import ImCube
        return ImCube.fromMetadata(self, lock)

    @cached_property
    def idTag(self) -> str:
        return f"ImCube_{self._dict['system']}_{self._dict['time']}"

    @property
    def wavelengths(self) -> Tuple[float, ...]:
        return self._dict['wavelengths']

    @classmethod
    def loadAny(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> ICMetaData:
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
        if lock is not None:
            lock.acquire()
        try:
            try:
                md = json.load(open(os.path.join(directory, 'pwsmetadata.txt')))
            except:  # have to use the old metadata
                info2 = list(spio.loadmat(os.path.join(directory, 'info2.mat'))['info2'].squeeze())
                info3 = list(spio.loadmat(os.path.join(directory, 'info3.mat'))['info3'].squeeze())
                print("Json metadata not found. Using backup metadata.")
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
        if lock is not None:
            lock.acquire()
        try:
            with h5py.File(os.path.join(directory, 'imageCube.mat'), 'r') as hf:
                cubeParams = hf['cubeParameters']
                lam = cubeParams['lambda']
                exp = cubeParams['exposure'] #we don't support adaptive exposure.
                md = {'startWv': lam['start'].value[0][0], 'stepWv': lam['step'].value[0][0], 'stopWv': lam['stop'].value[0][0],
                      'exposure': exp['base'].value[0][0], 'time': datetime.strptime(np.string_(cubeParams['metadata']['date'].value.astype(np.uint8)).decode(), '%Y%m%dT%H%M%S').strftime(dateTimeFormat),
                      'system': np.string_(cubeParams['metadata']['hardware']['system']['id'].value.astype(np.uint8)).decode(), 'wavelengths': list(lam['sequence'].value[0]),
                      'binning': None, 'pixelSizeUm': None}
        finally:
            if lock is not None:
                lock.release()
        return cls(md, filePath=directory, fileFormat=ICMetaData.FileFormats.NanoMat, acquisitionDirectory=acquisitionDirectory)

    @classmethod
    def fromTiff(cls, directory, lock: mp.Lock = None, acquisitionDirectory: Optional[AcqDir] = None) -> ICMetaData:
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
        with open(os.path.join(directory, 'pwsmetadata.json'), 'w') as f:
            json.dump(self._dict, f)

    def getThumbnail(self) -> np.ndarray:
        if self.fileFormat == ICMetaData.FileFormats.NanoMat:
            with h5py.File(os.path.join(self.filePath, 'image_bd.mat'), 'r') as hf:
                return np.array(hf['image_bd']).T.copy()  # For some reason these are saved transposed?
        else:
            with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
                return f.asarray()