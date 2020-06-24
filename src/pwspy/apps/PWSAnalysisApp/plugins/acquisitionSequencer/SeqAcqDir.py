from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.sequencerCoordinate import SequencerCoordinate
from pwspy.dataTypes import AcqDir
import os


class SeqAcqDir:
    def __init__(self, acq: AcqDir):
        self.acquisitionDirectory = acq
        path = os.path.join(acq.filePath, "sequencerCoords.json")
        self.sequencerCoordinate = SequencerCoordinate.fromJsonFile(path)
