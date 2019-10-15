from __future__ import annotations
from enum import Enum, auto
from typing import Optional, Tuple
import multiprocessing as mp
from ._MetaDataBaseClass import MetaDataBase
import os, json
import tifffile as tf
from pwspy.dataTypes import _jsonSchemasPath
import numpy as np
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import AcqDir


class DynMetaData(MetaDataBase):
    class FileFormats(Enum):
        Tiff = auto()

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'DynMetaData.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, metadata: dict, filePath: Optional[str], fileFormat: Optional[FileFormats] = None, acquisitionDirectory: Optional[AcqDir] = None):
        self.fileFormat = fileFormat
        super().__init__(metadata, filePath, acquisitionDirectory=acquisitionDirectory)

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
