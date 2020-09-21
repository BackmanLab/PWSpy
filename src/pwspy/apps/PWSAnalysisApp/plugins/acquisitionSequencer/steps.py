from __future__ import annotations
import abc
import enum
import json
import typing
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.item import SelfTreeItem
from pwspy.utility.micromanager import PositionList

StepTypeNames = dict(
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
    """Implementation of a TreeItem for representing a sequencer step."""
    def __init__(self, id: int, settings: dict, stepType: str, children: typing.List[SequencerStep] = None):
        super().__init__()
        self.id = id
        self.settings = settings
        self.stepType = stepType
        # self.setData(0, f"{Names[stepType]}")
        if children is not None:
            self.addChildren(children)

    @staticmethod
    def hook(dct: dict):
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
    
    def __repr__(self):
        return str(f"Step {self.id}: {self.stepType}")
    
    def printSubTree(self, _indent: int = 0):
        indent = ''.join((['\t'] * _indent))
        print(f"{indent}{self}")
        for child in self.children():
            child.printSubTree(_indent = _indent+1)


class ContainerStep(SequencerStep): pass


class CoordSequencerStep(ContainerStep):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abc.abstractmethod
    def stepIterations(self):  # return the total number of iterations of this step.
        raise NotImplementedError()

    @abc.abstractmethod
    def getIterationName(self, iteration: int) -> str:
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


