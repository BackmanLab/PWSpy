from __future__ import annotations
import json
import math
import os
import typing
from datetime import datetime
import cv2
import h5py
import numpy as np
from pwspy import dateTimeFormat
from pwspy.analysis import AbstractHDFAnalysisResults


class TransformedData(AbstractHDFAnalysisResults):
    FileSuffix = "_transformedData.h5"

    @classmethod
    def create(cls, templateIdTag: str, affineTransform: np.ndarray, transformedData: np.ndarray, methodName: str) -> TransformedData:  # Inherit docstring
        d = {'templateIdTag': templateIdTag,
             'affineTransform': affineTransform,
             'transformedData': transformedData,
             'methodName': methodName,
             'creationTime': datetime.now().strftime(dateTimeFormat)}
        return cls(None, d)

    @staticmethod
    def fields() -> typing.Tuple[str, ...]:
        return (
            'templateIdTag',  # The `IdTag` of the ITOMeasurement that was used as the `template` for this calibration analysis
            'affineTransform',  # A 2x3 matrix specifying the affine transformation between the template data and this data.
            'transformedData',  # The data after having been warped by `afffineTransform` invalid regions of data will be marked as numpy.nan
            'methodName',  # A string indicating the type of method used to determine which computer-vision method was used to determine the affine transform
            'creationTime'  # The timestamp indicating when this object was first created.
        )

    @AbstractHDFAnalysisResults.FieldDecorator
    def templateIdTag(self) -> str:
        return bytes(self.file['templateIdTag'][()]).decode()

    @AbstractHDFAnalysisResults.FieldDecorator
    def methodName(self) -> str:
        return bytes(self.file['methodName'][()]).decode()

    @AbstractHDFAnalysisResults.FieldDecorator
    def affineTransform(self) -> np.ndarray:
        return np.array(self.file['affineTransform'])

    @AbstractHDFAnalysisResults.FieldDecorator
    def transformedData(self) -> np.ndarray:
        return np.array(self.file['transformedData'])

    @AbstractHDFAnalysisResults.FieldDecorator
    def creationTime(self) -> str:
        """The time that the analysis was performed."""
        return bytes(self.file['creationTime'][()]).decode()

    @property
    def idTag(self) -> str:
        return f"{self.templateIdTag}_{self.creationTime}"

    def getValidDataSlice(self) -> typing.Tuple[slice, slice]:
        """Use the affine transformation from a calibration result to create a 2d slice that will select out only the valid parts of the data"""
        shape = self.transformedData.shape
        origRect = np.array([[0, 0], [shape[1], 0], [shape[1], shape[0]], [0, shape[0]]]).astype(np.float32)  # Coordinates are in X,Y format rather than row, column
        # Generate coordinates of corners of the original image after affine transformation.
        tRect = cv2.transform(origRect[None, :, :], cv2.invertAffineTransform(self.affineTransform))[0, :, :]  # For some reason this needs to be 3d for opencv to work.
        leftCoords = [tRect[0][0], tRect[3][0]]
        topCoords = [tRect[2][1], tRect[3][1]]
        rightCoords = [tRect[1][0], tRect[2][0]]
        bottomCoords = [tRect[0][1], tRect[1][1]]
        # Select the rectancle that fits entirely into the transformed corner coordinate set. That way all data is guaranteed to be valid.
        left = math.ceil(max(leftCoords))
        top = math.floor(min(topCoords))
        right = math.floor(min(rightCoords))
        bottom = math.ceil(max(bottomCoords))
        # Depending on which interpolation method is used to cv2.warpAffine the image array one pixel at the edge may be NaN. Crop one off each edge just in case.
        left += 1; right -= 1; top -= 1; bottom += 1
        # Make sure no coordinates lie outside the array indices
        left = max([0, left])
        top = min([shape[0], top])
        right = min([shape[1], right])
        bottom = max([0, bottom])
        slc = (slice(bottom, top), slice(left, right))  # A rectangular slice garaunteed to lie entirely inside the valid data aread, even if the transform has rotation.
        return slc

    @staticmethod
    def name2FileName(name: str) -> str:
        return f"{name}{TransformedData.FileSuffix}"

    @staticmethod
    def fileName2Name(fileName: str) -> str:
        """Provided with the full path to and HDF file containing results this function returns the 'name' used to save the file."""
        if not fileName.endswith(TransformedData.FileSuffix):
            raise NameError(f"{fileName} is not recognized as a TransformedData file.")
        return os.path.basename(fileName)[:-len(TransformedData.FileSuffix)]

    def toHDF(self, directory: str, name: str, overwrite: bool = False, compression: str = 'gzip'):
        """Override super-implementation to default to gzip compression of data. Cuts file size by more than half."""
        super().toHDF(directory, name, overwrite=overwrite, compression=compression)

    def addScore(self, name: str, scores: ScoreResults, overwrite: bool = False):
        if self.file is None:
            raise ValueError("Cannot save score to TransformedData that is not yet saved to file")
        if 'scores' not in self.file:
            self.file.create_group('scores')
        if overwrite and (name in self.file['scores']):
            del self.file['scores'][name]
        self.file['scores'].create_dataset(name, data=np.string_(scores.toJson()))

    def getScore(self, name: str) -> ScoreResults:
        if self.file is None:
            raise ValueError("Cannot load scores from TransformedData that is not yet saved to file")
        if 'scores' not in self.file:
            raise KeyError(f"No score named {name}")
        return ScoreResults.fromJson(bytes(self.file['scores'][name][()]).decode())

    def listScore(self) -> typing.Tuple[str, ...]:
        if self.file is None:
            raise ValueError("Cannot load scores from TransformedData that is not yet saved to file")
        if 'scores' not in self.file:
            return tuple()
        return tuple(self.file['scores'].keys())

    @classmethod
    def load(cls, directory: str, name: str) -> AbstractHDFAnalysisResults:
        """Load an analyis results object from an HDF5 file located in `directory`. We override the base class method so we can open the file as 'a' mode instead of 'r' so we can add scored to the file as we go.

        Args:
            directory: The path to the folder containing the file.
            name: The name of the analysis.
        Returns:
            A new instance of analysis results loaded from file.
        """
        import os.path as osp
        filePath = osp.join(directory, cls.name2FileName(name))
        if not osp.exists(filePath):
            raise OSError(f"The {cls.__name__} analysis file does not exist. {filePath}")
        file = h5py.File(filePath, 'a')
        return cls(file, None, name)


class ScoreResults:
    def __init__(self, scoresDict: dict):
        self.scores = scoresDict

    @classmethod
    def fromJson(cls, jsonStr: str):
        return cls(json.loads(jsonStr))

    def toJson(self) -> str:
        return json.dumps(self.scores, cls=ScoreResults.NumpyEncoder)

    class NumpyEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            else:
                return super().default(obj)
