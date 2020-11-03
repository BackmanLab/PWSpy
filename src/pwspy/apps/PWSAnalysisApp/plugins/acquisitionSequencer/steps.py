from __future__ import annotations
import abc
import enum
import json
import typing
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer._treeModel.item import SelfTreeItem
from pwspy.utility.micromanager import PositionList

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
    ZSTACK="Z-Stack"
)


class SequencerStep(SelfTreeItem):
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
        self.stepType = stepType
        if children is not None:
            self.addChildren(children)

    @staticmethod
    def hook(dct: dict):
        """
        This method defines how the JSON library should translate from JSON to one of these objects.
        Args:
            dct: The `dict` representing the raw representation of the JSON\
        """
        if all([i in dct for i in ("id", 'stepType', 'settings')]):
            clazz = SequencerStepTypes[dct['stepType']].value
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


class ContainerStep(SequencerStep):
    """
    A class for steps which can contain other steps within it.
    """
    pass


class CoordSequencerStep(ContainerStep):
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


class PositionsStep(CoordSequencerStep):
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


class TimeStep(CoordSequencerStep):
    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = self.settings['numFrames']
        return self._len

    def getIterationName(self, iteration: int) -> str:
        return f"{iteration * self.settings['frameIntervalMinutes']} min."


class ZStackStep(CoordSequencerStep):
    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = self.settings['numStacks']
        return self._len

    def getIterationName(self, iteration: int) -> str:
        return f"{iteration * self.settings['intervalUm']} μm"


class SequencerStepTypes(enum.Enum):
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


