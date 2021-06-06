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

# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 17:53:24 2018

@author: Nick Anthony
"""
from __future__ import annotations

import abc
import json
import typing
from dataclasses import dataclass
from numbers import Number
from typing import Union
import numpy as np
import copy
import matplotlib.pyplot as plt
import matplotlib as mpl
import scipy.io as spio
from pwspy.utility.micromanager.PropertyMap import PropertyMap, PropertyMapArray, Property, PropertyArray


@dataclass
class Position1d:
    """A 1D position usually describing the position of a Z-axis translation stage.

    Attributes:
        z: The position
        zStage: Then name of the translation stage
    """
    z: float    
    stageName: str = ''
    numAxes: int = 1

    def __post_init__(self):
        assert isinstance(self.z, float)
        assert isinstance(self.stageName, str)

    @staticmethod
    def fromDict(d: dict) -> Position1d:
        return Position1d(**d)

    def toPropertyMap(self) -> PropertyMap:
        return PropertyMap({"Device": Property(self.stageName),
                            "Position_um": PropertyArray([Property(self.z)])})

    @staticmethod
    def fromPropertyMap(pmap: PropertyMap) -> Position1d:
        if len(pmap['Position_um']) != 1:
            raise Exception("RERAR")
        return Position1d(z=pmap['Position_um'][0].value, zStage=pmap['Device'].value)

    def __repr__(self):
        return f"Position1d({self.stageName}, {self.z})"


@dataclass
class Position2d:
    """Represents a 2D position for a single xy stage in micromanager.

    Attributes:
        x: The x position
        y: The y position
        xyStage: The name of the 2 dimensional translation stage
    """
    x: float
    y: float
    stageName: str = ''
    numAxes: int = 2

    def __post_init__(self):
        assert isinstance(self.x, Number)
        assert isinstance(self.y, Number)
        assert isinstance(self.stageName, str)

    @staticmethod
    def fromDict(d: dict) -> Position2d:
        return Position2d(**d)

    def toPropertyMap(self) -> PropertyMap:
        return PropertyMap({"Device": Property(self.stageName),
                            "Position_um": PropertyArray([Property(self.x), Property(self.y)])})

    @staticmethod
    def fromPropertyMap(pmap: PropertyMap) -> Position2d:
        if len(pmap['Position_um']) != 2:
            raise Exception("Errr")
        x, y = pmap['Position_um'][0].value, pmap['Position_um'][1].value
        return Position2d(x=x, y=y, stageName=pmap['Device'].value)

    def mirrorX(self) -> Position2d:
        self.x *= -1
        return self

    def mirrorY(self) -> Position2d:
        self.y *= -1
        return self

    def renameStage(self, newName):
        self.stageName = newName

    def __repr__(self):
        return f"Position2d({self.stageName}, {self.x}, {self.y})"

    def __add__(self, other: Union[PositionList, Position2d, MultiStagePosition]) -> Union[PositionList, Position2d, MultiStagePosition]:
        if isinstance(other, PositionList):
            return other.__add__(self)
        elif isinstance(other, MultiStagePosition):
            return other.__add__(self)
        elif isinstance(other, Position2d):
            return Position2d(self.x + other.x,
                              self.y + other.y,
                              self.stageName)
        else:
            raise TypeError(f"Type {type(other)} is not supported.")

    def __sub__(self, other: Union[PositionList, Position2d, MultiStagePosition]) -> Union[PositionList, Position2d, MultiStagePosition]:
        if isinstance(other, PositionList):
            return other.copy().mirrorX().mirrorY().__add__(self)  # a-b == -b + a
        elif isinstance(other, MultiStagePosition):
            other = other.copy()  # Don't change the original object
            other.getXYPosition().mirrorX().mirrorY()  # invert the object.
            return other.__add__(self)  # a-b == -b + a
        elif isinstance(other, Position2d):
            return Position2d(self.x - other.x,
                              self.y - other.y,
                              self.stageName)
        else:
            raise TypeError(f"Type {type(other)} is not supported.")

    def __eq__(self, other: 'Position2d'):
        return all([self.x == other.x,
                    self.y == other.y,
                    self.stageName == other.stageName])


@dataclass
class MultiStagePosition:
    """Mirrors the class of the same name from Micro-Manager. Can contain multiple Positon1d or Position2d objects.
    Ideal for a system with multiple translation stages. It is assumed that there is only a single 2D stage and a single
    1D stage.

    Attributes:
        label: A name for the position
        xyStage: The name of the 2D stage
        zStage: The name of the 1D stage
        stagePositions: A list of `Position1d` and `Position2D` objects, usually just one of each.
    """
    label: str
    defaultXYStage: str
    defaultZStage: str
    stagePositions: typing.List[typing.Union[Position1d, Position2d]]
    gridRow: int = 0
    gridCol: int = 0

    @staticmethod
    def fromDict(d: dict) -> MultiStagePosition:
        sps = []
        for i in d['stagePositions']:
            if i['numAxes'] == 1:
                sps.append(Position1d.fromDict(i))
            elif i['numAxes'] == 2:
                sps.append(Position2d.fromDict(i))
            else:
                raise Exception()
        return MultiStagePosition(label=d['label'],
                                  defaultXYStage=d['defaultXYStage'],
                                  defaultZStage=d['defaultZStage'],
                                  stagePositions=sps,
                                  gridRow=d['gridRow'],
                                  gridCol=d['gridCol'])

    def toPropertyMap(self) -> PropertyMap:
        return PropertyMap({
            "DefaultXYStage": Property(self.defaultXYStage),
            "DefaultZStage": Property(self.defaultZStage),
            "DevicePositions": PropertyMapArray([i.toPropertyMap() for i in self.stagePositions]),
            "GridCol": Property(0),
            "GridRow": Property(0),
            "Label": Property(self.label),
            "Properties": PropertyMap({})
        })

    @staticmethod
    def fromPropertyMap(d: PropertyMap) -> MultiStagePosition:
        positions = []
        for i in d['DevicePositions']:
            if len(i["Position_um"]) == 1:
                positions.append(Position1d.fromPropertyMap(i))
            elif len(i["Position_um"]) == 2:
                positions.append(Position2d.fromPropertyMap(i))
            else:
                raise Exception("EEEEE")
        return MultiStagePosition(label=d['Label'].value, defaultXYStage=d['DefaultXYStage'].value, defaultZStage=d['DefaultZStage'].value,
                                  stagePositions=positions)

    def getXYPosition(self):
        """Return the first `Position2d` saved in the `positions` list"""
        d1pos = [i for i in self.stagePositions if isinstance(i, Position2d)]
        return [i for i in d1pos if i.stageName == self.defaultXYStage][0]

    def getZPosition(self):
        """Return the first `Position1d` saved in the positions` list. Returns `None` if no position is found."""
        try:
            d1pos = [i for i in self.stagePositions if isinstance(i, Position1d)]
            return [i for i in d1pos if i.stageName == self.defaultZStage][0]
        except IndexError:
            return None

    def renameXYStage(self, label: str):
        """Change the name of the xy stage.

        Args:
            label: The new name for the xy Stage
        """
        self.defaultXYStage = label
        self.getXYPosition().renameStage(label)

    def copy(self) -> MultiStagePosition:
        """Creates a copy fo the object

        Returns:
            A new `MultiStagePosition` object.
        """
        return copy.deepcopy(self)

    def __add__(self, other: Union[Position2d, MultiStagePosition, PositionList]) -> Union[MultiStagePosition, PositionList]:
        """Allow adding a position to another position or `PositionList`. Doesn't work on the Z-Axis but will sum together
        the X and Y axis values. Used to translate a position by an offset.

        Args:
            other: The object whose XY coordinates should be added to this objects XY coordinates.
        """
        if isinstance(other, Position2d):
            newPos = self.getXYPosition().__add__(other)
            positions = copy.copy(self.stagePositions)
            positions.remove(self.getXYPosition())
            positions.append(newPos)
            return MultiStagePosition(self.label, self.defaultXYStage, self.defaultZStage, stagePositions=positions)
        elif isinstance(other, MultiStagePosition):
            return self.__add__(other.getXYPosition())
        elif isinstance(other, PositionList):
            return other.__add__(self)
        else:
            raise NotImplementedError

    def __sub__(self, other: Union[Position2d, MultiStagePosition, PositionList]) -> Union[MultiStagePosition, PositionList]:
        """See the documentation for __add__"""
        if isinstance(other, Position2d):
            newPos = self.getXYPosition().__sub__(other)
            positions = copy.copy(self.stagePositions)
            positions.remove(self.getXYPosition())
            positions.append(newPos)
            return MultiStagePosition(self.label, self.defaultXYStage, self.defaultZStage, stagePositions=positions)
        elif isinstance(other, MultiStagePosition):
            return self.__sub__(other.getXYPosition())
        elif isinstance(other, PositionList):
            return other.copy().mirrorX().mirrorY().__add__(self)  # a-b == -b + a
        else:
            raise NotImplementedError

    def __eq__(self, other: MultiStagePosition):
        """Returns True if the stage names and stage coordinates are equivalent."""
        return all([self.defaultXYStage == other.defaultXYStage,
                    self.defaultZStage == other.defaultZStage,
                    self.getXYPosition() == other.getXYPosition(),
                    self.getZPosition() == other.getZPosition()])

    def __repr__(self):
        s = f"MultiStagePosition({self.label}, "
        for i in self.stagePositions:
            s += '\n\t' + i.__repr__()
        return s


class PositionList:
    """Represents a micromanager positionList. can be loaded from and saved to a micromanager .pos file.

    Args:
        positions: A list of `MultiStagePosition` objects

    Attributes:
        positions: A list of `MultiStagePosition` objects
    """

    def __init__(self, positions: typing.List[MultiStagePosition]):
        super().__init__()
        assert isinstance(positions, list)
        assert isinstance(positions[0], MultiStagePosition)
        self.positions = positions

    @staticmethod
    def fromDict(d: dict):
        p = []
        for i in d['positions']:
            p.append(MultiStagePosition.fromDict(i))
        return PositionList(p)

    def mirrorX(self) -> PositionList:
        """Invert all x coordinates

        Returns:
            A reference to this object.
        """
        for i in self.positions:
            i.getXYPosition().mirrorX()
        return self

    def mirrorY(self) -> PositionList:
        """Invert all y coordinates

         Returns:
             A reference to this object.
         """
        for i in self.positions:
            i.getXYPosition().mirrorY()
        return self

    def renameStage(self, label) -> PositionList:
        """Change the name of the xy stage.

        Args:
            label: The new name for the xy Stage

        Returns:
            A reference to this object
        """
        for i in self.positions:
            i.renameXYStage(label)
        return self

    def copy(self) -> PositionList:
        return copy.deepcopy(self)

    @staticmethod
    def fromPropertyMap(pmap: PropertyMap) -> PositionList:
        """Attempt to load a PositionList from a PropertyMap. May throw an exception."""
        if isinstance(pmap, PropertyMap):
            if "StagePositions" in pmap:
                return PositionList([MultiStagePosition.fromPropertyMap(i) for i in pmap["StagePositions"]])
        raise Exception("JsonParseException")

    def toPropertyMap(self) -> PropertyMap:
        """Returns the position list as a PropertyMap that is formatted just like a `PropertyMap` from Micro-Manager."""
        pmap = PropertyMap({"StagePositions": PropertyMapArray([i.toPropertyMap() for i in self.positions])})
        return pmap

    @classmethod
    def fromNanoMatFile(cls, path: str, xyStageName: str):
        """Load an instance of the `PositionList` from a file saved by NanoCytomics MATLAB acquisition software.

        Args:
            path: The file path to the .mat file.
            xyStageName: To adapt the MATLAB file format to the Micro-Manager we need to manually supply a name for the
            XY stage

        Returns:
            A new instance of `PositionList`
        """
        mat = spio.loadmat(path)
        l = mat['list']
        positions = []
        for i in range(l.shape[0]):
            coordString: str = l[i][0][0]
            x, y = coordString[1:-1].split(',')
            x, y = float(x), float(y)
            pos = Position2d(x, y, xyStageName)
            positions.append(MultiStagePosition(str(i), xyStageName, '', [pos]))
        return PositionList(positions)

    def toNanoMatFile(self, path: str):
        """Save this object to a .mat file in the format saved by NanoCytomics MATLAB acquistion software.

        Args:
            path: The file path for the new .mat file.
        """
        matPositions = []
        for pos in self.positions:
            pos = pos.getXYPosition()
            matPositions.append(f"({pos.x}, {pos.y})")
        matPositions = np.asarray(matPositions, dtype=np.object)
        print(matPositions.shape)
        spio.savemat(path, {'list': matPositions[:, None]})

    def getAffineTransform(self, otherList: PositionList) -> np.ndarray:
        """
        Calculate the partial affine transformation between this position list and another position list. Both position lists must have the same length

        Args:
            otherList (PositionList): A position list of the same length as this position list. Each position is assumed to correspond to the position of the
                same index in this list.

        Returns:
            np.ndarray: A 2x3 array representing the partial affine transform (rotation, scaling, and translation, but no skew)

        Examples:
            a = PositionList.fromNanoMatFile(r'F:/Data/AirDryingSystemComparison/NanoPreDry/corners/positions.mat', "TIXYDRIVE")
            b = PositionList.fromNanoMatFile(r'F:/Data/AirDryingSystemComparison/NanoPostDry/corners/positions.mat',"TIXYDRIVE")
            t = a.getAffineTransform(b)
            origPos = PositionList.fromNanoMatFile(r'F:/Data/AirDryingSystemComparison/NanoPreDry/0_8NA/position_list1.mat',"TIXYDRIVE")
            newPos = origPos.applyAffineTransform(t)
        """
        import cv2
        assert len(otherList) == len(self)
        selfXY = [pos.getXYPosition() for pos in self.positions]
        otherXY = [pos.getXYPosition() for pos in otherList.positions]
        selfArr = np.array([(pos.x, pos.y) for pos in selfXY], dtype=np.float32)
        otherArr = np.array([(pos.x, pos.y) for pos in otherXY], dtype=np.float32)
        transform, inliers = cv2.estimateAffinePartial2D(selfArr, otherArr)
        return transform

    def applyAffineTransform(self, t: np.ndarray):
        """Given an affine transformation array this method will transform all positions in this position list.
        Args:
            t (np.ndarray): A 2x3 array representing the partial affine transform (rotation, scaling, and translation, but no skew)
        """

        import cv2
        assert isinstance(t, np.ndarray)
        assert t.shape == (2, 3)
        selfXY = [pos.getXYPosition() for pos in self.positions]
        selfArr = np.array([[pos.x, pos.y] for pos in selfXY], dtype=np.float32)
        selfArr = selfArr[None, :, :]  # This is needed for opencv transform to work
        ret = cv2.transform(selfArr, t)
        positions = []
        for i in range(len(self)):
            pos = copy.deepcopy(self[i].getXYPosition())
            pos.x = float(ret[0, i, 0])  # Convert to float because the numpy number types cause some errors during jsonification.
            pos.y = float(ret[0, i, 1])
            positions.append(MultiStagePosition(self[i].label, self[i].defaultXYStage, '', [pos]))
        return PositionList(positions)

    def __repr__(self):
        s = "PositionList(\n["
        for i in self.positions:
            s += str(i) + '\n'
        s += '])'
        return s

    def __add__(self, other: Union[Position2d, MultiStagePosition, PositionList]) -> PositionList:
        if isinstance(other, Position2d):
            return PositionList([i + other for i in self.positions])
        elif isinstance(other, MultiStagePosition):
            self.__add__(other.getXYPosition())
        else:
            assert len(other) == len(self), "Cannot subtract position lists of different sizes"
            return PositionList([a + b for a, b in zip(self.positions, other.positions)])

    def __sub__(self, other: Union[Position2d, MultiStagePosition, PositionList]) -> PositionList:
        if isinstance(other, Position2d):
            return PositionList([i - other for i in self.positions])
        elif isinstance(other, MultiStagePosition):
            return self.__sub__(other.getXYPosition())
        else:
            assert len(other) == len(self), "Cannot subtract position lists of different sizes"
            return PositionList([a - b for a, b in zip(self.positions, other.positions)])

    def __len__(self):
        return len(self.positions)

    def __getitem__(self, idx: Union[slice, int]) -> MultiStagePosition:
        return self.positions[idx]

    def __eq__(self, other: PositionList):
        return all([len(self) == len(other)] +
                   [self[i] == other[i] for i in range(len(self))])

    def plot(self):
        """Open a matplotlib plot showing the positions contained in this list."""
        fig, ax = plt.subplots()
        annot = ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))
        annot.set_visible(False)
        ax.set_xlabel("x")
        ax.set_ylabel('y')
        ax.set_aspect('equal')
        cmap = mpl.cm.get_cmap("gist_rainbow")
        colors = [cmap(i) for i in np.linspace(0, 1, num=len(self.positions))]
        names = [pos.label for pos in self.positions]
        sc = plt.scatter([pos.getXYPosition().x for pos in self.positions], [pos.getXYPosition().y for pos in self.positions],
                         c=[colors[i] for i in range(len(self.positions))])

        def update_annot(ind):
            pos = sc.get_offsets()[ind["ind"][0]]
            annot.xy = pos
            text = "{}, {}".format(" ".join(list(map(str, ind["ind"]))),
                                   " ".join([names[n] for n in ind["ind"]]))
            annot.set_text(text)
            #            annot.get_bbox_patch().set_facecolor(cmap(norm(c[ind["ind"][0]])))
            annot.get_bbox_patch().set_alpha(0.4)

        def hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                cont, ind = sc.contains(event)
                if cont:
                    update_annot(ind)
                    annot.set_visible(True)
                    fig.canvas.draw_idle()
                else:
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", hover)


if __name__ == '__main__':
    path1 = r'C:\Users\nicke\Desktop\PositionList.pos'
    path2 = r'C:\Users\nicke\Desktop\PositionList5.pos'
    p = PropertyMap.loadFromFile(path1)
    pp = PositionList.fromPropertyMap(p)
    pp.mirrorX().mirrorY().mirrorX().mirrorY()
    ppp = pp.toPropertyMap()
    ppp.saveToFile(path2)
    with open(path1) as f1, open(path2) as f2:
        assert f1.read() == f2.read()
    a = 1


    def generateList(data: np.ndarray) -> PositionList:
        assert isinstance(data, np.ndarray)
        assert len(data.shape) == 2
        assert data.shape[1] == 2
        positions = []
        for n, i in enumerate(data):
            positions.append(MultiStagePosition(f'Cell{n + 1}', 'TIXYDrive', 'TIZDrive', stagePositions=[Position2d(i[0], i[1], 'TIXYDrive')]))
        plist = PositionList(positions)
        return plist


    def pws1to2(loadPath, newOriginX, newOriginY):
        if isinstance(loadPath, str):
            pws1 = PositionList.fromPropertyMap(PropertyMap.loadFromFile(loadPath))
        elif isinstance(loadPath, PositionList):
            pws1 = loadPath
        else:
            raise TypeError("loadPath must be either `str` or `PositionList`")
        pws2 = pws1.copy()
        pws2.mirrorX()
        pws2.mirrorY()
        pws2Origin = Position2d(newOriginX, newOriginY)
        offset = pws2Origin - pws2.positions[0]
        pws2 = pws2 + offset
        pws2.renameStage("TIXYDrive")
        return pws2


    def pws1toSTORM(loadPath, newOriginX, newOriginY):
        if isinstance(loadPath, str):
            pws1 = PositionList.fromPropertyMap(PropertyMap.loadFromFile(loadPath))
        elif isinstance(loadPath, PositionList):
            pws1 = loadPath
        else:
            raise TypeError("loadPath must be either `str` or `PositionList`")
        pws2 = pws1.copy()
        pws2.mirrorY()
        pws2Origin = Position2d(newOriginX, newOriginY)
        offset = pws2Origin - pws2.positions[0]
        pws2 = pws2 + offset
        pws2.renameStage("TIXYDrive")
        return pws2


    def pws2toSTORM(loadPath, newOriginX, newOriginY):
        if isinstance(loadPath, str):
            pws2 = PositionList.fromPropertyMap(PropertyMap.loadFromFile(loadPath))
        elif isinstance(loadPath, PositionList):
            pws2 = loadPath
        else:
            raise TypeError("loadPath must be either `str` or `PositionList`")
        storm = pws2.copy()
        storm.mirrorX()
        stormOrigin = Position2d(newOriginX, newOriginY)
        offset = stormOrigin - storm.positions[0]
        storm = storm + offset
        return storm


    def STORMtoPws2(loadPath, newOriginX, newOriginY):
        if isinstance(loadPath, str):
            storm = PositionList.fromPropertyMap(PropertyMap.loadFromFile(loadPath))
        elif isinstance(loadPath, PositionList):
            storm = loadPath
        else:
            raise TypeError("loadPath must be either `str` or `PositionList`")
        pws2 = storm.copy()
        pws2.mirrorX()
        pws2Origin = Position2d(newOriginX, newOriginY)
        offset = pws2Origin - pws2.positions[0]
        pws2 = pws2 + offset
        return pws2


    a = 1