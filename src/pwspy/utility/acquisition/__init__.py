import typing as t_
import warnings

from pwspy.utility.acquisition.steps import RuntimeSequenceSettings

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
    rtSeq = RuntimeSequenceSettings.fromJsonFile(directory)
    if rtSeq.uuid is None:
        warnings.warn("Old acquisition sequence file must have been loaded. No UUID found. Acquisitions returned by this function may not actually belong to this sequence.")

    files = glob(os.path.join(directory, '**', 'Cell[0-9]*'), recursive=True)
    acqs = []
    for f in files:
        try:
            acqs.append(SeqAcqDir(f))
        except FileNotFoundError:
            pass  # There may be "Cell" folders that don't contain a sequencer coordinate.
    acqs = [acq for acq in acqs if acq.sequencerCoordinate.uuid == rtSeq.uuid]  # Filter out acquisitions that don't have a matching UUID to the sequence file.
    # TODO verify that all expected acquisitions were found.
    return rtSeq.rootStep, acqs
