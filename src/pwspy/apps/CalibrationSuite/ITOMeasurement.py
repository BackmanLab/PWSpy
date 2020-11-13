import dataclasses
import logging
import os
import numpy as np
from pwspy import dataTypes as pwsdt
from pwspy.analysis import pws as pwsAnalysis
from glob import glob


class ITOMeasurement:
    ANALYSIS_NAME = 'ITOCalibration'

    def __init__(self, directory: str, settings: pwsAnalysis.PWSAnalysisSettings):
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

    @property
    def idTag(self) -> str:
        return self._itoAcq.pws.idTag + '||' + self._refAcq.idTag


@dataclasses.dataclass
class CalibrationResult:
    templateIdTag: str
    affineTransform: np.ndarray
