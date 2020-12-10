from __future__ import annotations
import dataclasses
import json
import logging
import os
import typing
import cv2
import h5py
import numpy as np
from pwspy import dataTypes as pwsdt
from pwspy.analysis import pws as pwsAnalysis, AbstractHDFAnalysisResults
from glob import glob

from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.utility.misc import cached_property
import math


class ITOMeasurement:
    """
    This class represents a single measurement of ITO thin film calibration. This consists of a raw acquisition of the ITO thin film
    as well as an acquisition of a reference image of a glass-water interface which is used for normalization.

    Args:
        directory: The file path to the folder containing both acquision folders.
    """

    ANALYSIS_NAME = 'ITOCalibration'

    def __init__(self, directory: str, settings: pwsAnalysis.PWSAnalysisSettings):
        self.filePath = os.path.abspath(directory)
        self.name = os.path.basename(directory)

        acqs = [pwsdt.AcqDir(f) for f in glob(os.path.join(directory, "Cell*"))]
        itoAcq = [acq for acq in acqs if acq.getNumber() < 900]
        assert len(itoAcq) == 1, "There must be one and only one ITO film acquisition. Cell number should be less than 900."
        self._itoAcq = itoAcq[0]
        refAcq = [acq for acq in acqs if acq.getNumber() > 900]
        assert len(refAcq) == 1, "There must be one and only one reference acquisition. Cell number should be greater than 900."
        self._refAcq = refAcq[0]

        if not self._hasAnalysis():
            self._results = self._generateAnalysis(settings)
        else:
            self._results: pwsAnalysis.PWSAnalysisResults = self._itoAcq.pws.loadAnalysis(self.ANALYSIS_NAME)
            assert self._results.settings == settings

    def _generateAnalysis(self, settings: pwsAnalysis.PWSAnalysisSettings) -> pwsAnalysis.PWSAnalysisResults:
        logger = logging.getLogger(__name__)
        logger.debug(f"Generating Analysis for {self.name}")
        ref = self._refAcq.pws.toDataClass()
        ref.correctCameraEffects()
        analysis = pwsAnalysis.PWSAnalysis(settings, None, ref)
        im = self._itoAcq.pws.toDataClass()
        im.correctCameraEffects()
        results, warnings = analysis.run(im)
        self._itoAcq.pws.saveAnalysis(results, self.ANALYSIS_NAME)
        return results

    def _hasAnalysis(self) -> bool:
        return self.ANALYSIS_NAME in self._itoAcq.pws.getAnalyses()

    @property
    def analysisResults(self) -> pwsAnalysis.PWSAnalysisResults:
        return self._results

    @cached_property
    def idTag(self) -> str:
        return self._itoAcq.pws.idTag.replace(':', '_') + '__' + self._refAcq.idTag.replace(':', '_') # We want this to be able to be used as a file name so sanitize the characters

    def saveCalibrationResult(self, result: CalibrationResult, overwrite: bool = False):
        if (result.templateIdTag in self.listCalibrationResults()) and (not overwrite):
            raise FileExistsError(f"A calibration result named {result.templateIdTag} already exists.")
        result.toHDF(self.filePath, result.templateIdTag, overwrite=overwrite)

    def loadCalibrationResult(self, templateIdTag: str) -> CalibrationResult:
        return CalibrationResult.load(self.filePath, templateIdTag)

    def listCalibrationResults(self) -> typing.Tuple[str]:
        return tuple([CalibrationResult.fileName2Name(f) for f in glob(os.path.join(self.filePath, f'*{CalibrationResult.FileSuffix}'))])


class TransformedData:
    def __init__(self, affineTransform: np.ndarray, transformedData: np.ndarray):
        self.affineTransform = affineTransform
        self.data = transformedData

    def getValidDataSlice(self) -> typing.Tuple[slice, slice]:
        """Use the affine transformation from a calibration result to create a 2d slice that will select out only the valid parts of the data"""
        shape = self.data.shape
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
        # Make sure no coordinates lie outside the array indices
        left = max([0, left])
        top = min([shape[0], top])
        right = min([shape[1], right])
        bottom = max([0, bottom])
        slc = (slice(bottom, top), slice(left, right))  # A rectangular slice garaunteed to lie entirely inside the valid data aread, even if the transform has rotation.
        return slc

class CalibrationResult(AbstractHDFAnalysisResults):
    """
    Represents the results from a single calibration to a template data cube. Can be easily saved/loaded to and HDF file.
    """

    FileSuffix = "_calResult.h5"

    @classmethod
    def create(cls, templateIdTag: str, affineTransform: np.ndarray, transformedData: np.ndarray, scores: dict) -> CalibrationResult:  # Inherit docstring
        d = {'templateIdTag': templateIdTag,
             'affineTransform': affineTransform,
             'transformedData': transformedData,
             'scores': scores}
        return cls(None, d)

    def toHDF(self, directory: str, name: str, overwrite: bool = False):
        """Overwrite super-implementation to default to compression of data. Cuts file size by more than half."""
        super().toHDF(directory, name, overwrite=overwrite, compression='gzip')

    @staticmethod
    def fields() -> typing.Tuple[str, ...]:
        return (
            'templateIdTag',  # The `IdTag` of the ITOMeasurement that was used as the `template` for this calibration analysis
            'affineTransform',  # A 2x3 matrix specifying the affine transformation between the template data and this data.
            'transformedData',  # The data after having been warped by `afffineTransform` invalid regions of data will be marked as numpy.nan
            'scores'  # A dictionary containing the various score outputs. TBD exactly what this contains.
        )

    @AbstractHDFAnalysisResults.FieldDecorator
    def templateIdTag(self) -> str:
        return bytes(self.file['templateIdTag']).decode()

    @AbstractHDFAnalysisResults.FieldDecorator
    def affineTransform(self) -> np.ndarray:
        return np.array(self.file['affineTransform'])

    @AbstractHDFAnalysisResults.FieldDecorator
    def transformedData(self) -> np.ndarray:
        return np.array(self.file['transformedData'])

    @AbstractHDFAnalysisResults.FieldDecorator
    def scores(self) -> dict:
        return json.loads(np.string_(self.file['transformedData']))

    @staticmethod
    def name2FileName(name: str) -> str:
        return f"{name}{CalibrationResult.FileSuffix}"

    @staticmethod
    def fileName2Name(fileName: str) -> str:
        """Provided with the full path to and HDF file containing results this function returns the 'name' used to save the file."""
        if not fileName.endswith(CalibrationResult.FileSuffix):
            raise NameError(f"{fileName} is not recognized as a calibration results file.")
        return os.path.basename(fileName)[:-len(CalibrationResult.FileSuffix)]


