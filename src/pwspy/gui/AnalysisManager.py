import os
import typing

from PyQt5.QtWidgets import QMessageBox

from pwspy import ImCube, CameraCorrection
from pwspy.analysis.analysisClass import Analysis
from pwspy.gui.analysis import PWSApp
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility import loadAndProcess


class AnalysisManager:
    def __init__(self, app: PWSApp):
        self.app = app

    def run(self):
        refMeta = self.app.window.cellSelector.getSelectedReferenceMeta()
        cellMetas = self.app.window.cellSelector.getSelectedCellMetas()
        cameraCorrection, settings = self.app.window.analysisSettings.getSettings()
        if cameraCorrection is None: # This means that we the user has selected automatic cameraCorrection
            correctionsOk = self._checkAutoCorrectionConsistency(cellMetas + [refMeta])
        else:
            correctionsOk = True #We're using a user provided camera correction so we assume it's good to go.
        if correctionsOk:
            ref = ImCube.fromMetadata(refMeta)
            if cameraCorrection is not None:
                ref.correctCameraEffects(cameraCorrection)
            else:
                print("Using automatically detected camera corrections")
                ref.correctCameraEffects(ref.cameraCorrection)
            analysis = Analysis(settings, ref)
            analysisName = self.app.window.analysisSettings.getAnalysisName()
            loadAndProcess(cellMetas, processorFunc=self._process, procArgs=[ref, analysis, analysisName],
                            parallel=True)

    @staticmethod
    def _process(im: ImCube, analysis: Analysis, analysisName: str, cameraCorrection: CameraCorrection):
        if cameraCorrection is not None:
            im.correctCameraEffects(cameraCorrection)
        else:
            im.correctCameraEffects(im.cameraCorrection)
        results = analysis.run(im)
        im.saveAnalysis(results, analysisName)

    def _checkAutoCorrectionConsistency(self, cellMetas: typing.List[ICMetaData]) -> bool:
        camCorrections = [i.cameraCorrection for i in cellMetas]
        names = [os.path.split(i.filePath)[-1] for i in cellMetas]
        missing, _ = zip(*[(name, cam) for name, cam in zip(names, camCorrections) if cam is None])
        if len(missing) > 0:
            missingMessage = str(missing) if len(missing) <= 3 else 'Many cells are'
            QMessageBox.information(self.app.window, 'Hmm', f'{missingMessage} missing automatic camera correction')
            return False
        if len(set([hash(i) for i in camCorrections])) > 1:
            QMessageBox.information(self.app.window, 'Hmm', "Multiple camera corrections are present in the set of selected cells.")
            return False
        return True