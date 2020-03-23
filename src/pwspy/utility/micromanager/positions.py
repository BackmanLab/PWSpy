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


class JsonAble(abc.ABC):
    @abc.abstractmethod
    def toDict(self) -> dict:
        pass


@dataclass
class Property(JsonAble):
    """Represents a single property from a micromanager PropertyMap"""
    name: str
    pType: str
    value: typing.Union[str, int, float, typing.List[typing.Union[str, int, float]]]

    def toDict(self):
        assert self.pType in ['STRING', 'DOUBLE', 'INTEGER']
        d = {'type': self.pType}
        if isinstance(self.value, list):
            d['array'] = self.value
        else:
            d['scalar'] = self.value
        return d

@dataclass
class PropertyMap(JsonAble):
    """Represents a propertyMap from micromanager. basically a list of properties."""
    name: str
    properties: typing.List[Union[Property, MultiStagePosition, Position1d, Position2d]]
            
    def toDict(self):
        if isinstance(self.properties[0], Property):
            d = {'type': 'PROPERTY_MAP',
                       'array': [{i.name: i for i in self.properties}]}
        elif isinstance(self.properties[0], (MultiStagePosition, Position1d, Position2d)):
            d = {'type': 'PROPERTY_MAP',
                       'array': [i.toDict() for i in self.properties]}
        else:
            raise TypeError(f"Got type of: {type(self.properties[0])}")
        return d

@dataclass   
class Position1d(JsonAble):  
    z: float    
    zStage: str = ''

    def __post_init__(self):
        assert isinstance(self.z, float)
        assert isinstance(self.zStage, str)
    
    def toDict(self):
        contents = [Property("Device", "STRING", self.zStage),
             Property("Position_um", "DOUBLE", [self.z])]
        return {i.name: i for i in contents}
        
    def __repr__(self):
        return f"Position1d({self.zStage}, {self.z})"

@dataclass
class Position2d(JsonAble):
    """Represents a position for a single xy stage in micromanager."""
    x: float
    y: float
    xyStage: str = ''

    def __post_init__(self):
        assert isinstance(self.x, Number)
        assert isinstance(self.y, Number)
        assert isinstance(self.xyStage, str)

    def toDict(self):
        contents = [Property("Device", "STRING", self.xyStage),
             Property("Position_um", "DOUBLE", [self.x, self.y])]
        return {i.name: i for i in contents}

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
    """Mirrors the class of the same name from Micro-Manager. Can contain multiple Positon1d or Position2d objects. Ideal for a system with multiple translation
    stages."""
    label: str
    xyStage: str
    zStage: str
    positions: typing.List[typing.Union[Position1d, Position2d]]
        
    def toDict(self):
        contents = [
            Property("DefaultXYStage", "STRING", self.xyStage),
            Property("DefaultZStage", "STRING", self.zStage), 
            PropertyMap("DevicePositions", self.positions),
            Property("GridCol", "INTEGER", 0),
            Property("GridRow", "INTEGER", 0),
            Property("Label", "STRING", self.label)]
        return {i.name: i for i in contents}
   
    def getXYPosition(self):
        d1pos = [i for i in self.positions if isinstance(i, Position2d)]
        return [i for i in d1pos if i.xyStage == self.xyStage][0]
    
    def getZPosition(self):
        try:
            d1pos = [i for i in self.positions if isinstance(i, Position1d)]
            return [i for i in d1pos if i.zStage == self.zStage][0]
        except IndexError:
            return None
    
    def renameXYStage(self, label: str):
        self.xyStage = label
        self.getXYPosition().renameStage(label)

    def copy(self) -> MultiStagePosition:
        return copy.deepcopy(self)

    def __add__(self, other: Union[Position2d, MultiStagePosition, PositionList]) -> Union[MultiStagePosition, PositionList]:
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
        return all([self.xyStage == other.xyStage,
                    self.zStage == other.zStage,
                    self.getXYPosition() == other.getXYPosition(),
                    self.getZPosition() == other.getZPosition()])
    
    def __repr__(self):
        s = f"MultiStagePosition({self.label}, "
        for i in self.positions:
            s+= '\n\t' + i.__repr__()
        return s


class PositionList(JsonAble):
    """Represents a micromanager positionList. can be loaded from and saved to a micromanager .pos file."""

    def __init__(self, positions: typing.List[MultiStagePosition]):
        assert isinstance(positions, list)
        assert isinstance(positions[0], MultiStagePosition)
        self.positions = positions

    def toDict(self):
        """Returns the position list as a dict that is formatted just like a `PropertyMap` from Micro-Manager."""
        return {"encoding": "UTF-8",
                   'format': 'Micro-Manager Property Map',
                   'major_version': 2,
                   'minor_version': 0,
                   "map": {"StagePositions": PropertyMap("StagePositions", self.positions)}}

    def mirrorX(self) -> PositionList:
        for i in self.positions:
            i.getXYPosition().mirrorX()
        return self

    def mirrorY(self) -> PositionList:
        for i in self.positions:
            i.getXYPosition().mirrorY()
        return self

    def renameStage(self, newName) -> PositionList:
        for i in self.positions:
            i.renameXYStage(newName)
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
        def _decode(dct):
            if 'format' in dct:
                if dct['format'] != 'Micro-Manager Property Map' or int(dct['major_version']) != 2:
                    raise Exception("The file format does not appear to be supported.")
                positions = []
                for i in dct['map']['StagePositions']['array']:
                    label = i['Label']['scalar']
                    xyStage = i["DefaultXYStage"]['scalar']
                    zStage = i["DefaultZStage"]['scalar']
                    xyDict = [j for j in i["DevicePositions"]['array'] if j['Device']['scalar'] == xyStage][0]
                    xyCoords = xyDict["Position_um"]['array']
                    mspPositions = [Position2d(*xyCoords, xyStage)]
                    try:
                        zDict = [j for j in i["DevicePositions"]['array'] if j['Device']['scalar'] == zStage][0]
                        zCoord = zDict['Position_um']['array'][0]
                        mspPositions.append(Position1d(zCoord, zStage))
                    except IndexError:
                        pass
                    positions.append(MultiStagePosition(label, xyStage, zStage, positions=mspPositions))
            else:
                return dct
            return PositionList(positions)

        if filePath[-4:] != '.pos':
            filePath += '.pos'
        with open(filePath, 'r') as f:
            return json.load(f, object_hook=_decode)

    @classmethod
    def fromNanoMatFile(cls, path: str, xyStageName: str):
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
        matPositions = []
        for pos in self.positions:
            pos = pos.getXYPosition()
            matPositions.append(f"({pos.x}, {pos.y})")
        matPositions = np.asarray(matPositions, dtype=np.object)
        print(matPositions.shape)
        spio.savemat(path, {'list': matPositions[:,None]})
    
    def getAffineTransform(self, otherList: PositionList) -> np.ndarray:
        """Calculate the partial affine transformation between this position list and another position list. Both position lists must have the same length
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

    class Encoder(json.JSONEncoder):
        """Allows for the position list and related objects to be jsonified."""
        def default(self, obj):
            if isinstance(obj, JsonAble):
                return obj.toDict()
            elif type(obj) == np.float32:
                return float(obj)
            else:
                return json.JSONEncoder(ensure_ascii=False).default(obj)

    def __len__(self):
        return len(self.positions)

    def __getitem__(self, idx: Union[slice, int]) -> MultiStagePosition:
        return self.positions[idx]

    def __eq__(self, other: PositionList):
        return all([len(self) == len(other)] +
                   [self[i] == other[i] for i in range(len(self))])

    def plot(self):
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
