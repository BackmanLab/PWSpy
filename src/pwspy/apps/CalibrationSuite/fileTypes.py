from __future__ import annotations
import json
import math
import os
import typing
from datetime import datetime
import cv2
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


class ScoreResults(AbstractHDFAnalysisResults):
    FileSuffix = "_calibrationScore.h5"

    @classmethod
    def create(cls, scores: dict, transformedDataIdTag: str) -> ScoreResults:  # Inherit docstring
        d = {'scores': scores,
             'transformedDataIdTag': transformedDataIdTag}
        return cls(None, d)

    @staticmethod
    def fields() -> typing.Tuple[str, ...]:
        return (
            'scores',
            'transformedDataIdTag'
        )

    @staticmethod
    def name2FileName(name: str) -> str:
        return f"{name}{ScoreResults.FileSuffix}"

    @staticmethod
    def fileName2Name(fileName: str) -> str:
        """Provided with the full path to and HDF file containing results this function returns the 'name' used to save the file."""
        if not fileName.endswith(ScoreResults.FileSuffix):
            raise NameError(f"{fileName} is not recognized as a ScoreResults file.")
        return os.path.basename(fileName)[:-len(ScoreResults.FileSuffix)]

    @AbstractHDFAnalysisResults.FieldDecorator
    def scores(self) -> dict:
        return json.loads(bytes(np.array(self.file['scores'])).decode())

    @AbstractHDFAnalysisResults.FieldDecorator
    def transformedDataIdTag(self) -> str:
        return bytes(np.array(self.file['transformeDataIdTag'])).decode()