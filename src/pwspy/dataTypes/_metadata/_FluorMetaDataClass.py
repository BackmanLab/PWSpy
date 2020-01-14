from __future__ import annotations
import json
from typing import Optional
import os
import tifffile as tf
from pwspy.dataTypes import _jsonSchemasPath
from ._MetaDataBaseClass import MetaDataBase
import numpy as np
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import AcqDir, FluorescenceImage

class FluorMetaData(MetaDataBase):
    FILENAME = 'fluor.tif'
    MDPATH = 'fluorMetadata.json'

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'MetaDataBase.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, md: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        super().__init__(md, filePath, acquisitionDirectory)

    def toDataClass(self) -> FluorescenceImage:
        from pwspy.dataTypes import FluorescenceImage
        return FluorescenceImage.fromMetadata(self)
    
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