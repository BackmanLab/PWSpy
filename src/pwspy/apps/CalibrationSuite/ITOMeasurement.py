from __future__ import annotations
import dataclasses
import logging
import os
import typing

import h5py
import numpy as np
from pwspy import dataTypes as pwsdt
from pwspy.analysis import pws as pwsAnalysis
from glob import glob

from pwspy.utility.misc import cached_property


class ITOMeasurement:
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
            self._generateAnalysis(settings)
        else:
            pass  # TODO check that settings match the previously done analysis

        self._results: pwsAnalysis.PWSAnalysisResults = self._itoAcq.pws.loadAnalysis(self.ANALYSIS_NAME)

    def _generateAnalysis(self, settings: pwsAnalysis.PWSAnalysisSettings):
        logger = logging.getLogger(__name__)
        logger.debug(f"Generating Analysis for {self.name}")
        ref = self._refAcq.pws.toDataClass()
        ref.correctCameraEffects()
        analysis = pwsAnalysis.PWSAnalysis(settings, None, ref)
        im = self._itoAcq.pws.toDataClass()
        im.correctCameraEffects()
        results, warnings = analysis.run(im)
        self._itoAcq.pws.saveAnalysis(results, self.ANALYSIS_NAME)

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
        result.toHDFFile(self.filePath, result.templateIdTag, overwrite=overwrite)

    def loadCalibrationResult(self, templateIdTag: str) -> CalibrationResult:
        return CalibrationResult.fromHDFFile(self.filePath, templateIdTag)

    def listCalibrationResults(self) -> typing.Tuple[str]:
        return tuple([CalibrationResult.fileName2Name(f) for f in glob(os.path.join(self.filePath, f'*{CalibrationResult.FileSuffix}'))])


@dataclasses.dataclass
class CalibrationResult:
    templateIdTag: str
    affineTransform: np.ndarray
    transformedData: np.ndarray

    FileSuffix = "_calResult.h5"

    def toHDFFile(self, directory: str, name: str, overwrite: bool = False):
        fName = os.path.join(directory, f'{name}_calResult.h5')
        if os.path.exists(fName) and (not overwrite):
            raise FileExistsError(f"The calibration results file {fName} already exists.")
        with h5py.File(fName, 'w') as hf:
            hf.create_dataset('transformedData', data=self.transformedData)
            hf.create_dataset('affineTransform', data=self.affineTransform)
            hf.create_dataset('templateIdTag', data=np.string_(self.templateIdTag))

    @classmethod
    def fromHDFFile(cls, directory: str, name: str):
        with h5py.File(os.path.join(directory, f"{name}{cls.FileSuffix}"), 'r') as hf:
            d = {}
            for field in dataclasses.fields(cls):
                dset = hf[field.name]
                if (h5py.check_string_dtype(dset.dtype)) is not None: # This is a string field
                    d[field.name] = bytes(np.array(dset)).decode()
                else:  # Must be a numpy array
                    d[field.name] = np.array(dset)
        return cls(**d)

    @classmethod
    def fileName2Name(cls, path: str):
        """Provided with the full path to and HDF file containing results this function returns the 'name' used to save the file."""
        if not path.endswith(cls.FileSuffix):
            raise NameError(f"{path} is not recognized as a calibration results file.")
        return os.path.basename(path)[:-len(cls.FileSuffix)]
