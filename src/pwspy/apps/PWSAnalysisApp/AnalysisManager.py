import os
from typing import Tuple, List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

from pwspy import ImCube, CameraCorrection, ExtraReflectanceCube
from pwspy.analysis import AnalysisSettings
from pwspy.analysis.analysisClass import Analysis
from pwspy.analysis.warnings import AnalysisWarning
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility import loadAndProcess


class AnalysisManager(QtCore.QObject):
    analysisDone = QtCore.pyqtSignal(str, AnalysisSettings, list)

    def __init__(self, app: 'PWSApp'):
        super().__init__()
        self.app = app

    def runList(self):
        for anName, anSettings, cellMetas, refMeta, camCorrection, erMeta in self.app.window.analysisSettings.getListedAnalyses():
            self.runSingle(anName, anSettings, cellMetas, refMeta, camCorrection, erMeta)

    def runSingle(self, anName: str, anSettings: AnalysisSettings, cellMetas: List[ICMetaData], refMeta: ICMetaData,
                  cameraCorrection: CameraCorrection, erMeta: ERMetadata) -> Tuple[str, AnalysisSettings, List[Tuple[List[AnalysisWarning], ICMetaData]]]:
        # refMeta = self.app.window.cellSelector.getSelectedReferenceMeta()
        # cellMetas = self.app.window.cellSelector.getSelectedCellMetas()
        # cameraCorrection, settings = self.app.window.analysisSettings.getSettings()
        if cameraCorrection is None: # This means that the user has selected automatic cameraCorrection
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
            erCube = ExtraReflectanceCube.fromMetadata(erMeta)
            analysis = Analysis(anSettings, ref, erCube)
            # analysisName = self.app.window.analysisSettings.getAnalysisName()
            warnings = loadAndProcess(cellMetas, processorFunc=self._process, procArgs=[ref, analysis, anName], parallel=True) # A list of Tuples. each tuple containing a list of warnings and the ICmetadata to go with it.
            warnings = [(warn, md) for warn, md in warnings if md is not None]
            ret = (anName, anSettings, warnings)
            self.analysisDone.emit(*ret)
            return ret

    @staticmethod
    def _process(im: ImCube, analysis: Analysis, analysisName: str, cameraCorrection: CameraCorrection):
        if cameraCorrection is not None:
            im.correctCameraEffects(cameraCorrection)
        else:
            im.correctCameraEffects(im.cameraCorrection)
        results, warnings = analysis.run(im)
        im.saveAnalysis(results, analysisName)
        if len(warnings) > 0:
            md = im.toMetadata()
        else:
            md = None
        return warnings, md

    def _checkAutoCorrectionConsistency(self, cellMetas: List[ICMetaData]) -> bool:
        camCorrections = [i.cameraCorrection for i in cellMetas]
        names = [os.path.split(i.filePath)[-1] for i in cellMetas]
        missing = []
        for name, cam in zip(names, camCorrections):
            if cam is None:
                missing.append(name)
        if len(missing) > 0:
            missingMessage = str(missing) if len(missing) <= 3 else 'Many cells are'
            QMessageBox.information(self.app.window, 'Hmm', f'{missingMessage} missing automatic camera correction')
            return False
        if len(set([hash(i) for i in camCorrections])) > 1:
            QMessageBox.information(self.app.window, 'Hmm', "Multiple camera corrections are present in the set of selected cells.")
            return False
        return True