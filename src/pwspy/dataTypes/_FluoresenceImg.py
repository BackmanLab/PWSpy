import numpy as np
import tifffile as tf
import os, json
from typing import Optional

class FluorescenceImage:
    FILENAME = 'fluor.tif'
    MDPATH = 'fluorMetadata.json'

    def __init__(self, data: np.ndarray, md: dict, filePath: Optional[str] = None):
        self.data = data
        self.metadata = md
        self.filePath = filePath

    @staticmethod
    def isValidPath(directory: str):
        path = os.path.join(directory, FluorescenceImage.FILENAME)
        path2 = os.path.join(directory, FluorescenceImage.MDPATH)
        return os.path.exists(path) and os.path.exists(path2)

    @classmethod
    def fromTiff(cls, directory: str):
        path = os.path.join(directory, FluorescenceImage.FILENAME)
        if not cls.isValidPath(directory):
            raise ValueError(f"Fluorescence image not found in {directory}.")
        img = tf.TiffFile(path)
        with open(os.path.join(directory, FluorescenceImage.MDPATH), 'r') as f:
            md = json.load(f)
        return cls(img.asarray(), md, directory)

    def toTiff(self, directory: str):
        with open(os.path.join(directory, FluorescenceImage.FILENAME), 'wb') as f:
            tf.imsave(f, self.data)
        with open(os.path.join(directory, FluorescenceImage.MDPATH), 'w') as f:
            json.dump(self.metadata, f)
