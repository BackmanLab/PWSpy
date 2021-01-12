from __future__ import annotations
import logging
import os
import typing
from pwspy import dataTypes as pwsdt
from pwspy.analysis import pws as pwsAnalysis, AbstractHDFAnalysisResults
from glob import glob

from pwspy.apps.CalibrationSuite.fileTypes import TransformedData, ScoreResults
from pwspy.dataTypes import AnalysisManager
from pwspy.utility.misc import cached_property


class ITOMeasurement(AnalysisManager):
    """
    This class represents a single measurement of ITO thin film calibration. This consists of a raw acquisition of the ITO thin film
    as well as an acquisition of a reference image of a glass-water interface which is used for normalization.

    Args:

    """

    ANALYSIS_NAME = 'ITOCalibration'

    def __init__(self, homeDir: str, itoAcq: pwsdt.AcqDir, refAcq: pwsdt.AcqDir, settings: pwsAnalysis.PWSAnalysisSettings, name: str):
        super().__init__(homeDir)
        self.filePath = os.path.abspath(homeDir)
        self.name = name
        self._itoAcq = itoAcq
        self._refAcq = refAcq

        if not os.path.exists(homeDir):
            os.makedirs(homeDir)

        logger = logging.getLogger(__name__)
        if not self._hasAnalysis():
            logger.debug(f"Generating analysis for {self.name}")
            results = self._generateAnalysis(settings)
        else:
            logger.debug(f"Loading cached analysis for {self.name}")
            results = self.analysisResults
            assert results.settings == settings  # Make sure the same settings were used for the previously stored analysis results.
            assert results.referenceIdTag == self._refAcq.idTag  # Make sure the same reference was used in the previously stored analysis results

    @staticmethod
    def getAnalysisResultsClass() -> typing.Type[AbstractHDFAnalysisResults]:
        return pwsAnalysis.PWSAnalysisResults

    def _generateAnalysis(self, settings: pwsAnalysis.PWSAnalysisSettings) -> pwsAnalysis.PWSAnalysisResults:

        ref = self._refAcq.pws.toDataClass()
        ref.correctCameraEffects()
        analysis = pwsAnalysis.PWSAnalysis(settings, None, ref)
        im = self._itoAcq.pws.toDataClass()
        im.correctCameraEffects()
        results, warnings = analysis.run(im)
        self.saveAnalysis(results, self.ANALYSIS_NAME)
        return results

    def _hasAnalysis(self) -> bool:
        return self.ANALYSIS_NAME in self.getAnalyses()

    @property
    def analysisResults(self) -> pwsAnalysis.PWSAnalysisResults:
        return self.loadAnalysis(self.ANALYSIS_NAME)

    @cached_property
    def idTag(self) -> str:
        return self._itoAcq.pws.idTag.replace(':', '_') + '__' + self._refAcq.idTag.replace(':', '_') # We want this to be able to be used as a file name so sanitize the characters

    def saveTransformedData(self, result: TransformedData, overwrite: bool = False):
        if (result.templateIdTag in self.listTransformedData()) and (not overwrite):
            raise FileExistsError(f"A calibration result named {result.templateIdTag} already exists.")
        result.toHDF(self.filePath, result.templateIdTag, overwrite=overwrite)

    def loadTransformedData(self, templateIdTag: str) -> TransformedData:
        try:
            return TransformedData.load(self.filePath, templateIdTag)
        except OSError:
            raise OSError(f"No TransformedData file found for template: {templateIdTag} for measurement: {self.name}")

    def listTransformedData(self) -> typing.Tuple[str]:
        return tuple([TransformedData.fileName2Name(f) for f in glob(os.path.join(self.filePath, f'*{TransformedData.FileSuffix}'))])

    def saveScoreResults(self, result: ScoreResults, name: str, overwrite: bool = False):
        if (name in self.listScoreResults()) and (not overwrite):
            raise FileExistsError(f"A ScoreResults file named {name} already exists.")
        result.toHDF(self.filePath, name, overwrite=overwrite)

    def loadScoreResults(self, name: str) -> ScoreResults:
        try:
            return ScoreResults.load(self.filePath, name)
        except OSError:
            raise OSError(f"No ScoreResults file found with name: {name} for measurement: {self.name}")

    def listScoreResults(self) -> typing.Tuple[str]:
        return tuple([ScoreResults.fileName2Name(f) for f in glob(os.path.join(self.filePath, f'*{ScoreResults.FileSuffix}'))])


