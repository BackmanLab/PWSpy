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
import json
import typing
from dataclasses import dataclass
from numbers import Number
from typing import Union

import numpy as np
import copy
import matplotlib.pyplot as plt
import matplotlib as mpl
import abc
import scipy.io as spio

class HookReg:
    def __init__(self):
        self._hooks = []

    def addHook(self, f):
        self._hooks.append(f)
        return self

    def getHook(self):
        def hook(d: dict):
            for h in self._hooks:
                d = h(d)
                if isinstance(d, dict):
                    continue
                else:
                    break
            return d
        return hook


class JsonAble(abc.ABC):

    @abc.abstractmethod
    def toDict(self) -> dict:
        """Convert the object to a `dict` matching the form that MicroManager saves the corresponding object to JSON."""
        pass

    @staticmethod
    @abc.abstractmethod
    def hook(d: dict):
        pass


@dataclass
class Property(JsonAble):
    """Represents a single property from a micromanager PropertyMap

    Attributes:
        name: The name of the property
        pType: The type of the property. may be 'STRING', 'DOUBLE', or 'INTEGER'
        value: The value of the propoerty. Should match the type given in `pType`
    """
    pType: str
    value: typing.Union[str, int, float, typing.List[typing.Union[str, int, float]]]
    pTypes = ['STRING', 'DOUBLE', 'INTEGER']

    def toDict(self):
        assert self.pType in Property.pTypes
        d = {'type': self.pType}
        if isinstance(self.value, list):
            d['array'] = self.value
        else:
            d['scalar'] = self.value

    @staticmethod
    def hook(d: dict):
        if 'type' in d and d['type'] in Property.pTypes:

            if 'array' in d:
                val = d['array']
            elif 'scalar' in d:
                val = d['scalar']
            else:
                return d
            return Property(pType=d['type'], value=val)
        else:
            return d

    def toPrimitive(self):
        return self.value

@dataclass
class PropertyMap(JsonAble):
    """Represents a propertyMap from micromanager. basically a list of properties.

    Attributes:
        properties: A list of properties
    """
    properties: typing.Dict[str, Union[Property, MultiStagePosition, Position1d, Position2d]]
            
    def toDict(self):
        # if isinstance(self.properties[0], Property):
        #     d = {'type': 'PROPERTY_MAP',
        #                'array': [i.toDict() for i in self.properties]}
        # elif isinstance(self.properties[0], (MultiStagePosition, Position1d, Position2d)):
        #     d = {'type': 'PROPERTY_MAP',
        #                'array': [i.toDict() for i in self.properties]}
        # else:
        #     raise TypeError(f"Got type of: {type(self.properties[0])}")
        d = {'type': 'PROPERTY_MAP',
             'array': [self.properties]}
        return d

    @staticmethod
    def hook(d: dict):
        if 'type' in d and d['type'] == "PROPERTY_MAP":
            if 'array' in d:
                return PropertyMap(d['array'])
            elif 'scalar' in d:
                return PropertyMap(d['scalar'])
        return d


@dataclass   
class Position1d(JsonAble):
    """A 1D position usually describing the position of a Z-axis translation stage.

    Attributes:
        z: The position
        zStage: Then name of the translation stage
    """
    z: float    
    zStage: str = ''

    def __post_init__(self):
        assert isinstance(self.z, float)
        assert isinstance(self.zStage, str)
    
    def toDict(self):
        contents = {"Device": Property("STRING", self.zStage),
                "Position_um": Property("DOUBLE", [self.z])}
        return contents
        

    @staticmethod
    def hook(d: dict):
        if "Device" in d and "Position_um" in d and len(d['Position_um'].toPrimitive())==1:
            return Position1d(z=d['Position_um'].toPrimitive()[0], zStage=d['Device'].toPrimitive())
        else:
            return d

    def __repr__(self):
        return f"Position1d({self.zStage}, {self.z})"

@dataclass
class Position2d(JsonAble):
    """Represents a 2D position for a single xy stage in micromanager.

    Attributes:
        x: The x position
        y: The y position
        xyStage: The name of the 2 dimensional translation stage
    """
    x: float
    y: float
    xyStage: str = ''

    def __post_init__(self):
        assert isinstance(self.x, Number)
        assert isinstance(self.y, Number)
        assert isinstance(self.xyStage, str)

    def toDict(self):
        contents = {"Device": Property("STRING", self.xyStage),
             "Position_um": Property("DOUBLE", [self.x, self.y])}
        return contents

    @staticmethod
    def hook(d: dict):
        if "Device" in d and "Position_um" in d and len(d['Position_um'].toPrimitive())==2:
            x, y = d['Position_um'].toPrimitive()
            return Position2d(x=x, y=y, xyStage=d['Device'].toPrimitive())
        else:
            return d

    def mirrorX(self):
        self.x *= -1

    def mirrorY(self):
        self.y *= -1

    def renameStage(self, newName):
        self.xyStage = newName

    def __repr__(self):
        return f"Position2d({self.xyStage}, {self.x}, {self.y})"

    def __add__(self, other: Union[PositionList, Position2d, MultiStagePosition]) -> Union[PositionList, Position2d, MultiStagePosition]:
        if isinstance(other, PositionList):
            return other.__add__(self)
        elif isinstance(other, MultiStagePosition):
            return other.__add__(self)
        elif isinstance(other, Position2d):
            return Position2d(self.x + other.x,
                          self.y + other.y,
                          self.xyStage)
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
                              self.xyStage)
        else:
            raise TypeError(f"Type {type(other)} is not supported.")

    def __eq__(self, other: 'Position2d'):
        return all([self.x == other.x,
                    self.y == other.y,
                    self.xyStage == other.xyStage])


@dataclass
class MultiStagePosition(JsonAble):
    """Mirrors the class of the same name from Micro-Manager. Can contain multiple Positon1d or Position2d objects.
    Ideal for a system with multiple translation stages. It is assumed that there is only a single 2D stage and a single
    1D stage.

    Attributes:
        label: A name for the position
        xyStage: The name of the 2D stage
        zStage: The name of the 1D stage
        positions: A list of `Position1d` and `Position2D` objects, usually just one of each.
    """
    label: str
    xyStage: str
    zStage: str
    positions: typing.List[typing.Union[Position1d, Position2d]]
        
    def toDict(self):
        contents = {
            "DefaultXYStage": Property("STRING", self.xyStage),
            "DefaultZStage": Property("STRING", self.zStage),
            "DevicePositions": PropertyMap(self.positions),
            "GridCol": Property("INTEGER", 0),
            "GridRow": Property("INTEGER", 0),
            "Label": Property("STRING", self.label)}
        return contents
   

    @staticmethod
    def hook(d: dict):
        if all([i in d for i in ["DefaultXYStage", "DefaultZStage","DevicePositions","GridCol","GridRow","Label"]]):
            return MultiStagePosition(label=d['Label'], xyStage=d['DefaultXYStage'], zStage=d['DefaultZStage'], positions=d['DevicePositions'])
        else:
            return d

    def getXYPosition(self):
        """Return the first `Position2d` saved in the `positions` list"""
        d1pos = [i for i in self.positions if isinstance(i, Position2d)]
        return [i for i in d1pos if i.xyStage == self.xyStage][0]
    
    def getZPosition(self):
        """Return the first `Position1d` saved in the positions` list. Returns `None` if no position is found."""
        try:
            d1pos = [i for i in self.positions if isinstance(i, Position1d)]
            return [i for i in d1pos if i.zStage == self.zStage][0]
        except IndexError:
            return None
    
    def renameXYStage(self, label: str):
        """Change the name of the xy stage.

        Args:
            label: The new name for the xy Stage
        """
        self.xyStage = label
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
            positions = copy.copy(self.positions)
            positions.remove(self.getXYPosition())
            positions.append(newPos)
            return MultiStagePosition(self.label, self.xyStage, self.zStage, positions=positions)
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
            positions = copy.copy(self.positions)
            positions.remove(self.getXYPosition())
            positions.append(newPos)
            return MultiStagePosition(self.label, self.xyStage, self.zStage, positions=positions)
        elif isinstance(other, MultiStagePosition):
            self.__sub__(other.getXYPosition())
        elif isinstance(other, PositionList):
            return other.copy().mirrorX().mirrorY().__add__(self)  # a-b == -b + a
        else:
            raise NotImplementedError
    
    def __eq__(self, other: MultiStagePosition):
        """Returns True if the stage names and stage coordinates are equivalent."""
        return all([self.xyStage == other.xyStage,
                    self.zStage == other.zStage,
                    self.getXYPosition() == other.getXYPosition(),
                    self.getZPosition() == other.getZPosition()])
    
    def __repr__(self):
        s = f"MultiStagePosition({self.label}, "
        for i in self.positions:
            s += '\n\t' + i.__repr__()
        return s


class PositionList(JsonAble):
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

    def toDict(self):
        """Returns the position list as a dict that is formatted just like a `PropertyMap` from Micro-Manager."""
        return {"encoding": "UTF-8",
                   'format': 'Micro-Manager Property Map',
                   'major_version': 2,
                   'minor_version': 0,
                   "map": {"StagePositions": PropertyMap(self.positions)}}

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

    def save(self, savePath: str):
        if savePath[-4:] != '.pos':
            savePath += '.pos'
        with open(savePath, 'w') as f:
            json.dump(self, f, cls=PositionList.Encoder)

    @classmethod
    def load(cls, filePath: str) -> PositionList:
        """Load a `PositionList` froma file saved by Micro-Manager

        Args:
            filePath: The file path to the .pos position list file.

        Returns:
            A new instance of `PositionList`
        """
        if filePath[-4:] != '.pos':
            filePath += '.pos'
        with open(filePath, 'r') as f:
            return json.load(f, object_hook=hr.getHook())

    @staticmethod
    def hook(dct: dict):
        if 'format' in dct:
            if dct['format'] != 'Micro-Manager Property Map' or int(dct['major_version']) != 2:
                raise Exception("The file format does not appear to be supported.")
            positions = []
            # for i in dct['map']['StagePositions'].properties:
            #     label = i['Label']['scalar']
            #     xyStage = i["DefaultXYStage"]['scalar']
            #     zStage = i["DefaultZStage"]['scalar']
            #     xyDict = [j for j in i["DevicePositions"]['array'] if j['Device']['scalar'] == xyStage][0]
            #     xyCoords = xyDict["Position_um"]['array']
            #     mspPositions = [Position2d(*xyCoords, xyStage)]
            #     try:
            #         zDict = [j for j in i["DevicePositions"]['array'] if j['Device']['scalar'] == zStage][0]
            #         zCoord = zDict['Position_um']['array'][0]
            #         mspPositions.append(Position1d(zCoord, zStage))
            #     except IndexError:
            #         pass
            #     positions.append(MultiStagePosition(label, xyStage, zStage, positions=mspPositions))
            return PositionList(dct['map']['StagePositions'].properties)
        else:
            return dct


    class Encoder(json.JSONEncoder):
        """Allows for the position list and related objects to be jsonified."""
        def default(self, obj):
            if isinstance(obj, JsonAble):
                return obj.toDict()
            elif type(obj) == np.float32:
                return float(obj)
            else:
                return json.JSONEncoder(ensure_ascii=False).default(obj)

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
        spio.savemat(path, {'list': matPositions[:,None]})
    
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
        selfArr = selfArr[None, :, :] # This is needed for opencv transform to work
        ret = cv2.transform(selfArr, t)
        positions = []
        for i in range(len(self)):
            pos = copy.deepcopy(self[i].getXYPosition())
            pos.x = ret[0, i, 0]
            pos.y = ret[0, i, 1]
            positions.append(MultiStagePosition(self[i].label, self[i].xyStage, '', [pos]))
        return PositionList(positions)

    def __repr__(self):
        s = "PositionList(\n["
        for i in self.positions:
            s += str(i) + '\n'
        s += '])'
        return s

    def __add__(self, other: Union[Position2d, MultiStagePosition]) -> PositionList:
        if isinstance(other, Position2d):
            return PositionList([i + other for i in self.positions])
        elif isinstance(other, MultiStagePosition):
            self.__add__(other.getXYPosition())
        else:
            raise NotImplementedError

    def __sub__(self, other: Union[Position2d, MultiStagePosition]) -> PositionList:
        if isinstance(other, Position2d):
            return PositionList([i - other for i in self.positions])
        elif isinstance(other, MultiStagePosition):
            return self.__sub__(other.getXYPosition())
        else:
            raise NotImplementedError

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


hr = HookReg().addHook(Property.hook).addHook(PropertyMap.hook).addHook(Position1d.hook).addHook(Position2d.hook).addHook(MultiStagePosition.hook).addHook(PositionList.hook)


if __name__ == '__main__':
    p = PositionList.load(r'C:\Users\nicke\Desktop\PositionList3.pos')
    def generateList(data: np.ndarray):
        assert isinstance(data, np.ndarray)
        assert len(data.shape) == 2
        assert data.shape[1] == 2
        positions = []
        for n, i in enumerate(data):
            positions.append(Position2d(*i, 'TIXYDrive', f'Cell{n + 1}'))
        plist = PositionList(positions)
        return plist


    def pws1to2(loadPath, newOriginX, newOriginY):
        if isinstance(loadPath, str):
            pws1 = PositionList.load(loadPath)
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
            pws1 = PositionList.load(loadPath)
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
            pws2 = PositionList.load(loadPath)
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
            storm = PositionList.load(loadPath)
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