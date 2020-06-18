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

from PyQt5 import QtCore
from PyQt5.QtCore import QFile, QTextStream
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QTreeWidgetItem, QApplication, QTreeWidget, QWidget, QHBoxLayout, QTextEdit, QScrollArea, \
    QStyle, QStyleFactory, QTableWidgetItem

from pwspy.utility.micromanager import PositionList

Names = dict(
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


class Step(QTreeWidgetItem):
    def __init__(self, id: int, settings: dict, stepType: str, children: typing.List[Step] = None):
        super().__init__(QTreeWidgetItem.UserType)
        self.id = id
        self.settings = settings
        self.stepType = stepType
        self.setText(0, f"{Names[stepType]}")
        if children is not None:
            self.addChildren(children)

    def __repr__(self):
        return f"Step: {self.stepType}"

    @staticmethod
    def hook(dct: dict):
        if all([i in dct for i in ("id", 'stepType', 'settings')]):
            clazz = Types[dct['stepType']].value
            s = clazz(**dct)
            return s
        else:
            return dct

    @staticmethod
    def fromJson(j: str) -> Step:
        return json.loads(j, object_hook=Step.hook)


# class TextOutputStep(Step):
#     outputs = []
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.ite
#     def registerTextOutput(self, out: typing.Callable):
#         self.outputs.append(out)
#



class CoordStep(Step):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setText(1, f"i={self.stepIterations()}")

    @abc.abstractmethod
    def stepIterations(self):  # return the total number of iterations of this step.
        raise NotImplementedError()


class PositionsStep(CoordStep):
    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = len(PositionList.fromDict(self.settings['posList']))
        return self._len


class TimeStep(CoordStep):
    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = self.settings['numFrames']
        return self._len


class ZStackStep(CoordStep):
    def stepIterations(self):
        if not hasattr(self, '_len'):
            self._len = self.settings['numStacks']
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
    ROOT = Step
    SUBFOLDER = Step
    ZSTACK = ZStackStep

class DictTreeView(QTreeWidget):
    def setDict(self, d: dict):
        self.clear()
        self._fillItem(self.invisibleRootItem(), d)

    @staticmethod
    def _fillItem(item: QTreeWidgetItem, value: typing.Union[dict, list]):
        """Recursively populate a tree item with children to match the contents of a `dict`"""
        item.setExpanded(True)
        if isinstance(value, dict):
            for key, val in value.items():
                child = QTreeWidgetItem()
                child.setText(0, f"{key}")
                item.addChild(child)
                if isinstance(val, (list, dict)):
                    DictTreeView._fillItem(child, val)
                else:
                    child.setText(1, f"{val}")
        elif isinstance(value, list):
            for val in value:
                child = QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    DictTreeView._fillItem(child, val)
                elif type(val) is list:
                    child.setText(0, '[list]')
                    DictTreeView._fillItem(child, val)
                else:
                    child.setText(0, val)
                    child.setExpanded(True)


class SequencerCoordinate:
    def __init__(self, treePath: typing.Sequence[int], iterations: typing.Sequence[int]):
        self.treePath = treePath
        self.iterations = iterations

    @staticmethod
    def fromDict(d: dict) -> SequencerCoordinate:
        return SequencerCoordinate(treePath=d['treeIdPath'], iterations=d["stepIterations"])

    @staticmethod
    def fromJsonFile(path: str) -> SequencerCoordinate:
        with open(path) as f:
            return SequencerCoordinate.fromDict(json.load(f))

if __name__ == '__main__':
    with open(r'C:\Users\nicke\Desktop\data\toast2\sequence.pwsseq') as f:
        s = Step.fromJson(f.read())
    import sys

    app = QApplication(sys.argv)
    # import qdarkstyle
    # dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
    # app.setStyleSheet(dark_stylesheet)

    W = QWidget()
    W.setLayout(QHBoxLayout())

    w = QTreeWidget()
    w.setColumnCount(2)
    w.addTopLevelItem(s)
    w.setIndentation(10)

    # t = QTextEdit()
    # scroll = QScrollArea()
    # scroll.setViewport(t)
    w2 = DictTreeView()
    w2.setColumnCount(2)
    w2.setIndentation(10)


    w.itemClicked.connect(lambda item, column: w2.setDict(item.settings))

    W.layout().addWidget(w)
    W.layout().addWidget(w2)


    W.show()
    app.exec()
    a = 1