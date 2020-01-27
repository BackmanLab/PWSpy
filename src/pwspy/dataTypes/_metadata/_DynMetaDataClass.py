from __future__ import annotations
from enum import Enum, auto
from typing import Optional, Tuple
import multiprocessing as mp
from ._MetaDataBaseClass import AnalysisManagerMetaDataBase
import os, json
import tifffile as tf
from pwspy.dataTypes import _jsonSchemasPath
import numpy as np
import typing
import scipy.io as spio

from ...analysis.dynamics import DynamicsAnalysisResults

if typing.TYPE_CHECKING:
    from pwspy.dataTypes import AcqDir, DynCube


class DynMetaData(AnalysisManagerMetaDataBase):
    class FileFormats(Enum):
        Tiff = auto()
        RawBinary = auto()

    @staticmethod
    def getAnalysisResultsClass(): return DynamicsAnalysisResults

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'DynMetaData.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, metadata: dict, filePath: Optional[str], fileFormat: Optional[FileFormats] = None, acquisitionDirectory: Optional[AcqDir] = None):
        self.fileFormat = fileFormat
        super().__init__(metadata, filePath, acquisitionDirectory=acquisitionDirectory)

    def toDataClass(self, lock: mp.Lock = None) -> DynCube:
        from pwspy.dataTypes import DynCube
        return DynCube.fromMetadata(self, lock)

    @property
    def idTag(self) -> str:
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
            info2 = list(spio.loadmat(os.path.join(directory, 'info2.mat'))['info2'].squeeze())
            info3 = list(spio.loadmat(os.path.join(directory, 'info3.mat'))['info3'].squeeze())
            wv = list(spio.loadmat(os.path.join(directory, 'WV.mat'))['WV'].squeeze())
            wv = [int(i) for i in wv]  # We will have issues saving later if these are numpy int types.
            assert all([i == wv[0] for i in wv]), "The wavelengths of the dynamics cube are not all identical."
            md = {
                #RequiredMetadata
                'exposure': info2[3],
                'time': '{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(
                    *[int(i) for i in [info3[8], info3[7], info3[6], info3[9], info3[10], info3[11]]]),
                'system': str(info3[0]),
                'binning': None,
                'pixelSizeUm': None,
                'wavelength': wv[0],
                'times': (i*info2[3] for i in range(len(wv))),  # We don't have any record of the times so we just have to assume it matches exactly with the exposure time, this is in milliseconds.
                #Extra metadata
                'startWv': info2[0], 'stepWv': info2[1], 'stopWv': info2[2],
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
