from __future__ import annotations
import numpy as np
import tifffile as tf
import os, json
from typing import Optional
import typing
if typing.TYPE_CHECKING:
    from ._AcqDir import AcqDir


class FluorescenceImage:
    FILENAME = 'fluor.tif'
    MDPATH = 'fluorMetadata.json'

    def __init__(self, data: np.ndarray, md: dict, filePath: Optional[str] = None, acquisitionDirectory: Optional[AcqDir] = None):
        self.data = data
        self.metadata = md
        self.filePath = filePath
        self.acquisitionDirectory = acquisitionDirectory

    @staticmethod
    def isValidPath(directory: str):
        path = os.path.join(directory, FluorescenceImage.FILENAME)
        path2 = os.path.join(directory, FluorescenceImage.MDPATH)
        return os.path.exists(path) and os.path.exists(path2)

    @classmethod
    def fromTiff(cls, directory: str, acquisitionDirectory: Optional[AcqDir] = None):
        path = os.path.join(directory, FluorescenceImage.FILENAME)
        if not cls.isValidPath(directory):
            raise ValueError(f"Fluorescence image not found in {directory}.")
        img = tf.TiffFile(path)
        with open(os.path.join(directory, FluorescenceImage.MDPATH), 'r') as f:
            md = json.load(f)
        return cls(img.asarray(), md, directory, acquisitionDirectory=acquisitionDirectory)

    def toTiff(self, directory: str):
        with open(os.path.join(directory, FluorescenceImage.FILENAME), 'wb') as f:
            tf.imsave(f, self.data)
        with open(os.path.join(directory, FluorescenceImage.MDPATH), 'w') as f:
            json.dump(self.metadata, f)

    def getThumbnail(self) -> np.ndarray:
        with tf.TiffFile(os.path.join(self.filePath, 'image_bd.tif')) as f:
            return f.asarray()