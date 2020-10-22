from pwspy.dataTypes import AcqDir
from .plugin import AcquisitionSequencerPlugin
import os
from glob import glob

from .sequencerCoordinate import SeqAcqDir
from .steps import SequencerStep

__all__ = ['SeqAcqDir', 'SequencerStep']

def loadDirectory(dir: str):
    seq = SequencerStep.fromJsonFile(os.path.join(dir, "sequence.pwsseq"))

    files = glob(os.path.join(dir, "Cell*"))
    acqs = []
    for f in files:
        try:
            acqs.append(SeqAcqDir(f))
        except FileNotFoundError:
            pass  # There may be "Cell" foldrers that don't contain a sequencer coordinate.
    return seq, acqs