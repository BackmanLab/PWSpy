import typing as t_
from .steps import SequencerStep
from .sequencerCoordinate import SeqAcqDir
import os
from glob import glob


def loadDirectory(directory: str) -> t_.Tuple[SequencerStep, t_.List[SeqAcqDir]]:
    """
    If `directory` contains a dataset acquired with the acquisition sequencer then this function will return a python
    object representing the sequence settings and a list of references to the acquisitions that are part of the sequence.

    Args:
        directory: The file path to the dataset directory.

    Returns:
        A tuple containing:
            The Root `SequencerStep` of the acquisition sequence.
            A list of `SeqAcqDir` objects belonging to the sequence.
    """
    seq = SequencerStep.fromJsonFile(os.path.join(directory, "sequence.pwsseq"))

    files = glob(os.path.join(directory, '**', 'Cell[0-9]*'), recursive=True)
    acqs = []
    for f in files:
        try:
            acqs.append(SeqAcqDir(f))
        except FileNotFoundError:
            pass  # There may be "Cell" folders that don't contain a sequencer coordinate.
    # TODO verify that detected Acqs actually belong to this sequence.
    # TODO verify that all expected acquisitions were found.
    return seq, acqs