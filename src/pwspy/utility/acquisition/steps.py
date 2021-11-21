from __future__ import annotations
import abc
import enum
import json
import typing
from ._treeItem import TreeItem
from pwspy.utility.micromanager import PositionList
import os
from .sequencerCoordinate import SequencerCoordinateRange

StepTypeNames = dict(  # The names to represent the `steps` that can be in an acquisition sequence
    ACQ="Acquisition",
    POS="Multiple Positions",
    TIME="Time Series",
    CONFIG="Configuration Group",
    SUBFOLDER="Enter Subfolder",
    EVERYN="Once per `N` iterations",
    PFS="Optical Focus Lock",
    PAUSE="Pause",
    ROOT="Initialization",
    AF="Software Autofocus",
    ZSTACK="Z-Stack",
    AUTOSHUTTER='AutoShutter',
    WAIT="Wait"
)


class SequencerStep(TreeItem):
    """Implementation of a TreeItem for representing a sequencer step.

    Args:
        id: The unique integer assigned to this step by the acquisition software
        settings: The settings for this step. Saved as JSON in the sequence file.
        stepType: Indicates what type of step this is. E.g. acquisition, time-series, focus lock, etc.
        children: A list of steps which are direct children of this step.
    """
    def __init__(self, id: int, settings: dict, stepType: str, children: typing.List[SequencerStep] = None):
        super().__init__()
        self.id = id
        self.settings = settings
        self._stepType = stepType
        if children is not None:
            self.addChildren(children)

    @property
    def stepType(self) -> str:
        return self._stepType

    @staticmethod
    def hook(dct: dict):
        """
        This method defines how the JSON library should translate from JSON to one of these objects.
        Args:
            dct: The `dict` representing the raw representation of the JSON\
        """
        if all([i in dct for i in ("id", 'stepType', 'settings')]):
            clazz = _SequencerStepTypes[dct['stepType']].value
            s = clazz(**dct)
            return s
        else:
            return dct

    @staticmethod
    def fromJson(j: str) -> SequencerStep:
        return json.loads(j, object_hook=SequencerStep.hook)
    
    @staticmethod
    def fromJsonFile(filePath: str) -> SequencerStep:
        with open(filePath, 'r') as f:
            return json.loads(f.read(), object_hook=SequencerStep.hook)
    
    def __repr__(self):  # Text representation of this object.
        return str(f"Step {self.id}: {self.stepType}")

    def printSubTree(self, _indent: int = 0) -> None:
        """
        Print out this step and all sub-steps in a human-readable format.
        """
        indent = ''.join((['\t'] * _indent))
        print(f"{indent}{self}")
        for child in self.children():
            child.printSubTree(_indent=_indent+1)

    def getCoordinate(self) -> SequencerCoordinateRange:
        """Returns a sequencer coordinate range that points to this steps location in the tree of steps."""
        return SequencerCoordinateRange([(step.id, None) for step in self.getTreePath()])

    def __getitem__(self, item: int):
        """Enable [i] subscripting to get a child step"""
        return self.children()[item]


class ContainerStep(SequencerStep):
    """
    A class for steps which can contain other steps within it.
    """
    pass


class IterableSequencerStep(ContainerStep):
    """
    A base-class for steps which are iterable. Despite only being a single step they run multiple times in an acquisition.
    This add some complications as we want to keep track of which iteration the sub-steps of this belong to.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abc.abstractmethod
    def stepIterations(self):
        """
        Return the total number of iterations of this step.
        """
        raise NotImplementedError()

    @abc.abstractmethod
    def getIterationName(self, iteration: int) -> str:
        """
        Return the name associated with `iteration` E.G. for a multiple-positions step this will be the name assigned to the position in the position list.
        Args:
            iteration: The iteeration number we are interested in.

        Returns: A name for the requested iteration.

        """
        raise NotImplementedError()


class PositionsStep(IterableSequencerStep):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._positionList = PositionList.fromDict(self.settings['posList'])

    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = len(self._positionList)
        return self._len

    def getIterationName(self, iteration: int) -> str:
        return self._positionList[iteration].label

    def getPositionList(self) -> PositionList:
        return self._positionList


class TimeStep(IterableSequencerStep):
    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = self.settings['numFrames']
        return self._len

    def getIterationName(self, iteration: int) -> str:
        return f"{iteration * self.settings['frameIntervalMinutes']} min."


class ZStackStep(IterableSequencerStep):
    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = self.settings['numStacks']
        return self._len

    def getIterationName(self, iteration: int) -> str:
        return f"{iteration * self.settings['intervalUm']} μm"


class _SequencerStepTypes(enum.Enum):
    """
    An enumerator containing the sub-class of `SequencerStep` to use for each type of step.
    """
    ACQ = SequencerStep
    PFS = ContainerStep
    POS = PositionsStep
    TIME = TimeStep
    AF = SequencerStep
    CONFIG = ContainerStep
    PAUSE = SequencerStep
    EVERYN = ContainerStep
    ROOT = ContainerStep
    SUBFOLDER = ContainerStep
    ZSTACK = ZStackStep
    AUTOSHUTTER = ContainerStep
    WAIT = SequencerStep


class RuntimeSequenceSettings:
    """
    This represents the object saved when a new acquisition is run.
    """
    FILENAME = "sequence.rtpwsseq"
    OLDFILENAME = "sequence.pwsseq"

    def __init__(self, uuid: str, dateString: str, rootStep: SequencerStep):
        self.uuid = uuid
        self.dateString = dateString
        self.rootStep = rootStep

    @classmethod
    def fromJsonFile(cls, directory: str):
        if os.path.exists(os.path.join(directory, cls.FILENAME)):
            with open(os.path.join(directory, cls.FILENAME), 'r') as f:
                return cls(**json.load(f, object_hook=SequencerStep.hook))
        elif os.path.exists(os.path.join(directory, cls.OLDFILENAME)):
            with open(os.path.join(directory, cls.OLDFILENAME)) as f:
                rootStep = json.load(f, object_hook=SequencerStep.hook)
            return cls(uuid=None, dateString=None, rootStep=rootStep)  # Old sequence files didn't have a uuid or date. Too bad
        else:
            raise FileNotFoundError(f"No valid sequence file found in: {directory}")