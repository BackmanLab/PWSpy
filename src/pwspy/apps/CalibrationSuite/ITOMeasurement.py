import os

from pwspy import dataTypes as pwsdt
from pwspy.analysis import pws as pwsAnalysis


class ITOMeasurement:
    ANALYSIS_NAME = 'ITOCalibration'
    def __init__(self, directory: str, settings: pwsAnalysis.PWSAnalysisSettings):
        self.name = os.path.basename(directory)
        itoAcq = os.path.join(directory, "Cell1")
        self._itoAcq = pwsdt.AcqDir(itoAcq)
        refAcq = os.path.join(directory, "Cell999")
        self._refAcq = pwsdt.AcqDir(refAcq)

        if not self._hasAnalysis():
            self._generateAnalysis(settings)
        else:
            pass # TODO check that settings match the preiously don't analysis

        self._results: pwsAnalysis.PWSAnalysisResults = self._itoAcq.pws.loadAnalysis(self.ANALYSIS_NAME)

    def _generateAnalysis(self, settings: pwsAnalysis.PWSAnalysisSettings):
        ref = self._refAcq.pws.toDataClass()
        ref.correctCameraEffects()
        analysis = pwsAnalysis.PWSAnalysis(settings, None, ref)
        im = self._itoAcq.pws.toDataClass()
        im.correctCameraEffects()
        results = analysis.run(im)
        self._itoAcq.pws.saveAnalysis(results, self.ANALYSIS_NAME)

    def _hasAnalysis(self) -> bool:
        return self.ANALYSIS_NAME in self._itoAcq.pws.getAnalyses()

    @property
    def analysisResults(self) -> pwsAnalysis.PWSAnalysisResults:
        return self._results

    @property
    def idTag(self) -> str:
        return self._itoAcq.pws.idTag + '||' + self._refAcq.idTag

    # @property
    # def meanReflectance(self) -> np.ndarray:
    #     return self._results.meanReflectance
    #
    # @property
    # def reflectance(self) -> pwsdt.KCube:
    #     return self._results.reflectance