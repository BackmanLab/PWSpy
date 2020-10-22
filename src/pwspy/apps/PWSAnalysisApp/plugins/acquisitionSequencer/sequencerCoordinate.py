from __future__ import annotations
import json
import typing
import os
from pwspy.dataTypes import AcqDir


class SequencerCoordinateStep:
    """The contribution of a sequencer coordinate from a single step"""
    def __init__(self, id: int, iteration: int = None):
        self.stepId = id  # All steps should have a unique id number
        self.iteration = iteration  # Most steps will keep this as None, iterable steps will have an iteration.

    def __eq__(self, other: SequencerCoordinateStep):
        return self.stepId == other.stepId and self.iteration == other.iteration

    def __repr__(self):
        s = f"Step(ID:{self.stepId}"
        if self.iteration is not None:
            s += f", i:{self.iteration}"
        s += ")"
        return s

class SequencerCoordinate:
    def __init__(self, coordSteps: typing.List[SequencerCoordinateStep]):
        """treePath should be a list of the id numbers for each step in the path to this coordinate.
        iterations should be a list indicating which iteration of each step the coordinate was from."""
        self.fullPath = tuple(coordSteps)

    def __repr__(self):
        return f"SeqCoord:{self.fullPath}"

    @staticmethod
    def fromDict(d: dict) -> SequencerCoordinate:
        c = []
        for id, iteration in zip(d['treeIdPath'], d["stepIterations"]):
            c.append(SequencerCoordinateStep(id, iteration))
        return SequencerCoordinate(c)

    @staticmethod
    def fromJsonFile(path: str) -> SequencerCoordinate:
        with open(path) as f:
            return SequencerCoordinate.fromDict(json.load(f))

    def isSubPathOf(self, other: SequencerCoordinate):
        """Check if `self` is a parent path of the `item` coordinate """
        assert isinstance(other, SequencerCoordinate)
        if len(self.fullPath) >= len(other.fullPath):
            return False
        return self.fullPath == other.fullPath[:len(self.fullPath)]

    @property
    def iterations(self) -> typing.Sequence[int]:
        return tuple(i.iteration for i in self.fullPath)

    @property
    def ids(self) -> typing.Sequence[int]:
        return tuple(i.stepId for i in self.fullPath)

    def __eq__(self, other: SequencerCoordinate):
        """Check if these coordinates are identical"""
        assert isinstance(other, SequencerCoordinate)
        return self.fullPath == other.fullPath

class IterationRangeCoordStep:
    """Represents a coordinate for a single step that accepts multiple iterations"""
    def __init__(self, id: int, iterations: typing.Sequence[int] = None):
        self.stepId = id
        self.iterations = iterations  #Only iterable step types will have this, most types will keep this as None

    def __contains__(self, item: SequencerCoordinateStep):
        if self.stepId == item.stepId:
            if self.iterations is None:  # This step doesn't have any iterations so there is no need to check anything.
                return True
            elif len(self.iterations) == 0:  # If the accepted iterations are empty then we accept any iteration
                return True
            elif item.iteration in self.iterations:
                return True
        return False


class SequencerCoordinateRange:
    def __init__(self, coordSteps: typing.Sequence[IterationRangeCoordStep]):
        self.fullPath = tuple(coordSteps)

    def __contains__(self, item: SequencerCoordinate):
        """Returns True if this is a subpath of `item` and the iteration at each step lies within the range of acceptable iterations for this object"""
        if not isinstance(item, SequencerCoordinate):
            return False
        for i, coordRange in enumerate(self.fullPath):
            if not (item.fullPath[i] in coordRange):
                return False
        return True


class SeqAcqDir(AcqDir):
    def __init__(self, directory: typing.Union[str, AcqDir]):
        if isinstance(directory, AcqDir):
            directory = directory.filePath
        super().__init__(directory)
        path = os.path.join(directory, "sequencerCoords.json")
        self.sequencerCoordinate = SequencerCoordinate.fromJsonFile(path)

    def __repr__(self):
        return f"SeqAcqDir({self.filePath})"


