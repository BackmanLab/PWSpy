# Copyright © 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
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

@author: Nick Anthony
"""
from __future__ import annotations

import abc
import enum
import typing
import json
from logging import RootLogger


class Step:
    def __init__(self, id: int, settings: str, stepType: str, children: typing.List[Step] = None):
        self.id = id
        self.settings = settings
        self.stepType = stepType
        self.children = children

    def setChildren(self, children: typing.List[Step]):
        self.children = children

    @staticmethod
    def hook(dct: dict):
        if all([i in dct for i in ("id", 'stepType', 'settings')]):
            clazz = Types[dct['stepType']].value
            s = clazz(**dct)
            # if 'children' in dct:
            #     s.setChildren(dct['children'])
            return s
        else:
            return dct

    @staticmethod
    def fromJson(j: str):
        return json.loads(j, object_hook=Step.hook)


class RootStep(Step):
    pass

class CoordStep(Step, abc.ABC):
    @abc.abstractmethod
    def __len__(self): pass  # return the total number of iterations of this step.

class PositionsStep(CoordStep):
    def __len__(self):
        if not hasattr(self, '_len'):
            self._len = len(json.loads(self.settings)['posList']['positions_'])
        return self._len

class TimeStep(CoordStep):
    def __len__(self):
        if not hasattr(self, '_len'):
            self._len = json.loads(self.settings)['numFrames']
        return self._len

class ZStackStep(CoordStep):
    def __len__(self):
        if not hasattr(self, '_len'):
            self._len = json.loads(self.settings)['numStacks']
        return self._len

class Types(enum.Enum):
    ACQ = Step
    PFS = Step
    POS = PositionsStep
    TIME = TimeStep
    AF = Step
    CONFIG = Step
    PAUSE = Step
    EVERYN = Step
    ROOT = RootStep
    SUBFOLDER = Step
    ZSTACK = ZStackStep

#
# class SequenceCoordinate:
#     def __init__(self, path: typing.Sequence[int], coord: Coord):

if __name__ == '__main__':
    with open(r'C:\Users\nicke\Desktop\demo\sequence.pwsseq') as f:
        s = Step.fromJson(f.read())
    a = 1