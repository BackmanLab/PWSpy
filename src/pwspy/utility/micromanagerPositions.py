# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 17:53:24 2018

@author: backman05
"""
import json
import typing
from dataclasses import dataclass

import numpy as np
import copy
import matplotlib.pyplot as plt
import matplotlib as mpl
from abc import ABC, abstractmethod

class JsonAble(ABC):
    
    @abstractmethod
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
    properties: typing.List[Property]
            
    def toDict(self):
        if isinstance(properties[0], Property):
            d = {'type': 'PROPERTY_MAP',
                       'array': [{i.name: i for i in self.properties}]}
        elif isinstance(properties[0], Position2d):
            d = {'type': 'PROPERTY_MAP',
                       'array': [i.toDict() for i in self.properties]}
        else:
            raise TypeError   
        return d

@dataclass
class MultiStagePosition(JsonAble):
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
   
    def __repr__(self):
        return f"MultiStagePosition({self.label}, {i.__repr__() for i in self.positions})"

@dataclass   
class Position1d(JsonAble):  
    z: float    
    zStage: str    
    
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
    xyStage: str

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

    def __add__(self, other: 'Position2d') -> 'Position2d':
        assert isinstance(other, Position2d)
        return Position2d(self.x + other.x,
                          self.y + other.y,
                          self.xyStage,
                          self.label)

    def __sub__(self, other: 'Position2d') -> 'Position2d':
        assert isinstance(other, Position2d)
        return Position2d(self.x - other.x,
                          self.y - other.y,
                          self.xyStage,
                          self.label)

    def __eq__(self, other: 'Position2d'):
        return all([self.x == other.x,
                    self.y == other.y,
                    self.label == other.label,
                    self.xyStage == other.xyStage])
    
    def toDict(self):
        return self._d


class PositionList(JsonAble):
    """Represents a micromanager positionList. can be loaded from and saved to a micromanager .pos file."""

    def __init__(self, positions: typing.List[MultiStagePosition]):
        self.positions = positions
        self._regen()

    def _regen(self):
        self._d = {"encoding": "UTF-8",
                   'format': 'Micro-Manager Property Map',
                   'major_version': 2,
                   'minor_version': 0,
                   "map": {"StagePositions": PropertyMap("StagePositions", self.positions)}}

    def mirrorX(self):
        for i in self.positions:
            i.mirrorX()
        self._regen()

    def mirrorY(self):
        for i in self.positions:
            i.mirrorY()
        self._regen()

    def renameStage(self, newName):
        for i in self.positions:
            i.renameStage(newName)
        self._regen()

    def copy(self) -> 'PositionList':
        return copy.deepcopy(self)

    def save(self, savePath: str):
        #    a=json.dumps(plist,cls=Encoder, ensure_ascii=False)
        #    a = a.replace('{','{\n').replace('[','[\n').replace('}','\n}').replace(',',',\n').replace(']','\n]')
        if savePath[-4:] != '.pos':
            savePath += '.pos'
        with open(savePath, 'w') as f:
            json.dump(self, f, cls=PositionList.Encoder)

    @classmethod
    def load(cls, filePath: str) -> 'PositionList':
        def _decode(dct):
            if 'format' in dct:
                if dct['format'] == 'Micro-Manager Property Map' and int(dct['major_version']) == 2:
                    positions = []
                    for i in dct['map']['StagePositions']['array']:
                        label = i['Label']['scalar']
                        xyStage = i["DefaultXYStage"]['scalar']
                        zStage = i["DefaultZStage"]['scalar']
                        xyDict = [j for j in i["DevicePositions"]['array'] if j['Device']['scalar'] == xyStage][0]
                        zDict = [j for j in i["DevicePositions"]['array'] if j['Device']['scalar'] == zStage][0]
                        xyCoords = xyDict["Position_um"]['array']
                        positions.append(MultiStagePosition(label, xyStage, zStage,
                                                            positions=[
                                                                    Position2d(*xyCoords, xyStage),
                                                                    Position1d(zCoord, zStage)])
            else:
                return dct
            return PositionList(positions)

        with open(filePath, 'r') as f:
            return json.load(f, object_hook=_decode)

    def __repr__(self):
        s = "PositionList(\n["
        for i in self.positions:
            s += str(i) + '\n'
        s += '])'
        return s

    def __add__(self, other: Position2d) -> 'PositionList':
        assert isinstance(other, Position2d)
        return PositionList([i + other for i in self.positions])

    def __sub__(self, other: Position2d) -> 'PositionList':
        assert isinstance(other, Position2d)
        return PositionList([i - other for i in self.positions])

    class Encoder(json.JSONEncoder):
        """Allows for the position list and related objects to be jsonified."""
        def default(self, obj):
            if isinstance(obj, JsonAble):
                return obj.toDict()
            else:
                return json.JSONEncoder(ensure_ascii=False).default(self, obj)

    def __len__(self):
        return len(self.positions)

    def __getitem__(self, idx: slice):
        return self.positions[idx]

    def __eq__(self, other: 'PositionList'):
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
        sc = plt.scatter([pos.x for pos in self.positions], [pos.y for pos in self.positions],
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
        pws2 = storm.copy()
        pws2.mirrorX()
        pws2Origin = Position2d(newOriginX, newOriginY)
        offset = pws2Origin - pws2.positions[0]
        pws2 = pws2 + offset
        return pws2
