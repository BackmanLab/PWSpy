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
import json
import typing
from dataclasses import dataclass
import numpy as np


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
    def encode(self) -> dict:
        pass

    @staticmethod
    @abc.abstractmethod
    def hook(d: dict):
        pass

    @abc.abstractmethod
    def toDict(self):
        pass

    @staticmethod
    def dictEncode(d):
        if isinstance(d, list):
            D = []
            for i in d:
                D.append(JsonAble.dictEncode(i))
            return D
        elif isinstance(d, dict):
            D = {}
            for k, v in d.items():
                D[k] = JsonAble.dictEncode(v)
            return D
        elif isinstance(d, JsonAble):
            return JsonAble.dictEncode(d.toDict())
        else:
            return d

    class _Encoder(json.JSONEncoder):
        """Allows for the position list and related objects to be jsonified."""
        def default(self, obj):
            if isinstance(obj, JsonAble):
                return obj.encode()
            elif type(obj) == np.float32:
                return float(obj)
            else:
                return json.JSONEncoder(ensure_ascii=False).default(obj)

@dataclass
class Property(JsonAble):
    """Represents a single property from a micromanager PropertyMap

    Attributes:
        pType: The type of the property. may be 'STRING', 'DOUBLE', or 'INTEGER'
        value: The value of the propoerty. Should match the type given in `pType`
    """
    pType: str
    value: typing.Union[str, int, float, typing.List[typing.Union[str, int, float]]]
    pTypes = ['STRING', 'DOUBLE', 'INTEGER']

    def encode(self) -> dict:
        d = {'type': self.pType}
        if isinstance(self.value, list):
            d['array'] = self.value
        else:
            d['scalar'] = self.value
        return d

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

    def toDict(self):
        return self.value



@dataclass
class PropertyMap(JsonAble):
    """Represents a propertyMap from micromanager. basically a list of properties.

    Attributes:
        properties: A list of properties
    """
    properties: typing.Union[typing.Dict[str, Property], typing.List]

    def encode(self) -> dict:
        if len(self.properties) == 0:
            return {'type': 'PROPERTY_MAP',
                    'scalar': {}}
        else:
            return {'type': 'PROPERTY_MAP',
                    'array': self.properties}

    @staticmethod
    def hook(d: dict):
        if 'type' in d and d['type'] == "PROPERTY_MAP":
            if 'array' in d:
                return PropertyMap(d['array'])
            elif 'scalar' in d:
                return PropertyMap(d['scalar'])
        return d

    def toDict(self):
        return self.properties

@dataclass
class PropertyMapFile(JsonAble):
    mapName: str
    pMap: PropertyMap

    @staticmethod
    def hook(dct: dict):
        if 'format' in dct:
            if dct['format'] != 'Micro-Manager Property Map' or int(dct['major_version']) != 2:
                raise Exception("The file format does not appear to be supported.")
            k, v = next(iter(dct['map'].items()))
            return PropertyMapFile(k, v)
        else:
            return dct

    def encode(self) -> dict:
        return {"encoding": "UTF-8",
                'format': 'Micro-Manager Property Map',
                'major_version': 2,
                'minor_version': 0,
                "map": {self.mapName: self.pMap}}

    def toDict(self):
        return self.pMap

    @staticmethod
    def loadFromFile(path: str):
        with open(path) as f:
            return json.load(f, object_hook=hr.getHook())

    def saveToFile(self, path: str):
        with open(path, 'w') as f:
            json.dump(self, f, cls=JsonAble._Encoder, indent=2)


hr = HookReg().addHook(Property.hook).addHook(PropertyMap.hook).addHook(PropertyMapFile.hook)#.addHook(Position1d.hook).addHook(Position2d.hook).addHook(MultiStagePosition.hook).addHook(PositionList.hook)

if __name__ == '__main__':
    with open(r'C:\Users\nicke\Desktop\PositionList3.pos') as f:
        p = json.load(f, object_hook=hr.getHook())
    p.saveToFile(r'C:\Users\nicke\Desktop\PositionList4.pos')
    a = JsonAble.dictEncode(p)
    a = 1