from __future__ import annotations
import json
import typing as t_
import os
from pwspy.dataTypes import AcqDir


class SequencerCoordinate:
    """
    A coordinate that fully defines a position within a `tree` of steps.

    Args:
        coordSteps: A sequence of tuples of the form (stepId, stepIteration) where `stepId` is the id number of the step being referred to.
            If the step is an iterable step (multiple position, timeseries, etc.) then `stepIteration` should indicate the iteration number,
            otherwise it should be `None`.
        uuid: A universally unique ID string associated with the run of the sequencer that this coordinate is associated with.
    """
    def __init__(self, coordSteps: t_.Sequence[t_.Tuple[int, int]], uuid: str):
        self._fullPath = tuple(coordSteps)
        self.uuid = uuid  # Matches the uuid of the sequence file that ran this acquisition.

    def __repr__(self):
        return f"SeqCoord:{self._fullPath}"

    @staticmethod
    def fromDict(d: dict) -> SequencerCoordinate:
        c = []
        for ID, iteration in zip(d['treeIdPath'], d["stepIterations"]):
            c.append((ID, iteration))
        if 'uuid' in d:
            uuid = d['uuid']
        else:
            uuid = None
        return SequencerCoordinate(c, uuid)

    @staticmethod
    def fromJsonFile(path: str) -> SequencerCoordinate:
        with open(path) as f:
            return SequencerCoordinate.fromDict(json.load(f))

    def isSubPathOf(self, other: SequencerCoordinate):
        """Check if `self` is a parent path of the `item` coordinate """
        assert isinstance(other, SequencerCoordinate)
        if len(self._fullPath) >= len(other._fullPath):
            return False
        return self._fullPath == other._fullPath[:len(self._fullPath)]

    @property
    def iterations(self) -> t_.Sequence[int]:
        return tuple(iteration for ID, iteration in self._fullPath)

    @property
    def ids(self) -> t_.Sequence[int]:
        return tuple(ID for ID, iteration in self._fullPath)

    def __eq__(self, other: SequencerCoordinate):
        """Check if these coordinates are identical"""
        assert isinstance(other, SequencerCoordinate)
        return self._fullPath == other._fullPath


class IterationRangeCoordStep:
    """Represents a coordinate for a single step that accepts multiple iterations"""
    def __init__(self, id: int, iterations: t_.Sequence[int] = None):
        self.stepId = id
        self.iterations = iterations  #Only iterable step types will have this, most types will keep this as None

    def __contains__(self, item: t_.Tuple[int, int]):
        """
        Args:
            item: A tuple of form (stepId, iteration). See the documentation for SequencerCoordinate
        """
        if self.stepId == item[0]:
            if self.iterations is None:  # This step doesn't have any iterations so there is no need to check anything.
                return True
            elif len(self.iterations) == 0:  # If the accepted iterations are empty then we accept any iteration
                return True
            elif item[1] in self.iterations:
                return True
        return False


class SequencerCoordinateRange:
    """
    A coordinate that can have multiple iterations selected at once.
    """
    def __init__(self, coordSteps: t_.Sequence[IterationRangeCoordStep]):
        self.fullPath = tuple(coordSteps)

    def __contains__(self, item: SequencerCoordinate):
        """Returns True if this is a subpath of `item` and the iteration at each step lies within the range of acceptable iterations for this object"""
        if not isinstance(item, SequencerCoordinate):
            return False
        for i, coordRange in enumerate(self.fullPath):
            if not (item._fullPath[i] in coordRange):
                return False
        return True


class SeqAcqDir(AcqDir):
    """
    A subclasss of AcqDir that has will also search for a sequencerCoordinate file
    and load it as an attribute.
    """
    def __init__(self, directory: t_.Union[str, AcqDir]):
        if isinstance(directory, AcqDir):
            directory = directory.filePath
        super().__init__(directory)
        path = os.path.join(directory, "sequencerCoords.json")
        self.sequencerCoordinate = SequencerCoordinate.fromJsonFile(path)

