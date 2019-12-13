import json
from typing import Optional
import os
from pwspy.dataTypes import AcqDir
import tifffile as tf
from pwspy.dataTypes import _jsonSchemasPath
from pwspy.dataTypes._metadata._MetaDataBaseClass import MetaDataBase
import numpy as np

class FluorMetaData(MetaDataBase):
    FILENAME = 'fluor.tif'
    MDPATH = 'fluorMetadata.json'

    _jsonSchemaPath = os.path.join(_jsonSchemasPath, 'MetaDataBase.json')
    with open(_jsonSchemaPath) as f:
        _jsonSchema = json.load(f)

    def __init__(self, md: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        super().__init__(md, filePath, acquisitionDirectory)

    @classmethod
    def fromTiff(cls, directory: str, acquisitionDirectory: Optional[AcqDir]):
        if not FluorMetaData.isValidPath(directory):
            raise ValueError(f"Fluorescence image not found in {directory}.")
        with open(os.path.join(directory, FluorMetaData.MDPATH), 'r') as f:
            dic = json.load(f)
        return FluorMetaData(dic, directory, acquisitionDirectory)

    @staticmethod
    def isValidPath(directory: str):
        path = os.path.join(directory, FluorMetaData.FILENAME)
        path2 = os.path.join(directory, FluorMetaData.MDPATH)
        return os.path.exists(path) and os.path.exists(path2)

    def getThumbnail(self) -> np.ndarray:
        with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
            return f.asarray()