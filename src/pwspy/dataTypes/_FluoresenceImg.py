from __future__ import annotations
import numpy as np
import tifffile as tf
import os, json
from typing import Optional
import typing
from .metadata import FluorMetaData
import multiprocessing as mp
if typing.TYPE_CHECKING:
    from ._AcqDir import AcqDir


class FluorescenceImage:
    def __init__(self, data: np.ndarray, md: FluorMetaData):
        self.data = data
        self.metadata = md

    @classmethod
    def fromTiff(cls, directory: str, acquisitionDirectory: Optional[AcqDir] = None):
        md = FluorMetaData.fromTiff(directory, acquisitionDirectory) #This will raise an error if the folder isn't valid
        return cls.fromMetadata(md)

    @classmethod
    def fromMetadata(cls, md: FluorMetaData, lock: mp.Lock = None):
        path = os.path.join(md.filePath, FluorMetaData.FILENAME)
        if lock is not None:
            lock.acquire()
        try:
            img = tf.TiffFile(path)
        finally:
            if lock is not None:
                lock.release()
        return cls(img.asarray(), md)

    def toTiff(self, directory: str):
        with open(os.path.join(directory, FluorMetaData.FILENAME), 'wb') as f:
            tf.imsave(f, self.data)
        with open(os.path.join(directory, FluorMetaData.MDPATH), 'w') as f:
            json.dump(self.metadata, f)
