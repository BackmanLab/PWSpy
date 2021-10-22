# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

"""
This package includes functionality for loading experiment information saved by the PWS "Acquisition Sequencer" which is part of the PWS plugin
for Micro-Manager.

Functions
----------
.. autosummary::
   :toctree: generated/

   loadDirectory

Classes
---------
.. autosummary::
   :toctree: generated/

   RuntimeSequenceSettings
   SequenceAcquisition
   SequencerCoordinate
   SequencerCoordinateRange
   SequencerStep
   IterableSequencerStep
   ZStackStep
   TimeStep
   PositionsStep
   ContainerStep

Inheritance
-------------
.. inheritance-diagram:: TreeItem SequencerStep IterableSequencerStep ZStackStep TimeStep PositionsStep ContainerStep RuntimeSequenceSettings SequenceAcquisition SequencerCoordinate SequencerCoordinateRange
    :parts: 1

"""

import typing as t_
import warnings

from pwspy.utility.acquisition.steps import RuntimeSequenceSettings

from .steps import SequencerStep, IterableSequencerStep, ZStackStep, TimeStep, PositionsStep, ContainerStep
from ._treeItem import TreeItem
from .sequencerCoordinate import SequenceAcquisition, SequencerCoordinate, SequencerCoordinateRange
import os
import pwspy.dataTypes as pwsdt
from glob import glob


def loadDirectory(directory: os.PathLike) -> t_.Tuple[SequencerStep, t_.List[SequenceAcquisition]]:
    """
    If `directory` contains a dataset acquired with the acquisition sequencer then this function will return a python
    object representing the sequence settings and a list of references to the acquisitions that are part of the sequence.

    Args:
        directory: The file path to the dataset directory.

    Returns:
        A tuple containing:
            The Root `SequencerStep` of the acquisition sequence.
            A list of `SequenceAcquisition` objects belonging to the sequence.
    """
    rtSeq = RuntimeSequenceSettings.fromJsonFile(directory)
    if rtSeq.uuid is None:
        warnings.warn("Old acquisition sequence file must have been loaded. No UUID found. Acquisitions returned by this function may not actually belong to this sequence.")

    files = glob(os.path.join(directory, '**', 'Cell[0-9]*'), recursive=True)
    acqs = []
    for f in files:
        try:
            acqs.append(SequenceAcquisition(pwsdt.Acquisition(f)))
        except FileNotFoundError:
            pass  # There may be "Cell" folders that don't contain a sequencer coordinate.
    acqs = [acq for acq in acqs if acq.sequencerCoordinate.uuid == rtSeq.uuid]  # Filter out acquisitions that don't have a matching UUID to the sequence file.
    # TODO verify that all expected acquisitions were found.
    return rtSeq.rootStep, acqs
