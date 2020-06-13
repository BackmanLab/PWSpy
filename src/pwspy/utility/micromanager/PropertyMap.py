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
    """Stores json deserialization hooks and combines them into `getHook`"""
    def __init__(self):
        self._hooks = []

    def addHook(self, f):
        self._hooks.append(f)
        return self

    def getHook(self):
        def hook(d: dict):
            for h in self._hooks:
                origD = d
                d = h(d)
                if d is origD:
                    continue
                else:
                    return d
            return d
        return hook


class _JsonAble(abc.ABC):
    """
    Base class used for converting Micromanager Property map objects to/from JSON.
    """
    _hr = HookReg()  #This keeps track of the various deserialization hooks and combines them. pass _hr.getHook() to the json.load function.

    @staticmethod
    def registerClass(cls: typing.Type[_JsonAble]):
        _JsonAble._hr.addHook(cls.hook)

    @abc.abstractmethod
    def encode(self) -> dict:
        """This method should convert the property map class to a dictionary for jsonization"""
        pass

    @staticmethod
    @abc.abstractmethod
    def hook(d: object):
        """This function should try to identify if the provided JSON object (int, float, string, list, dict) represents an instance of this Property map class. If so then generate the class, otherwire return the input value unchanged."""
        pass

    class _Encoder(json.JSONEncoder):
        """Use this encoder to make use of the custom `encode` functionality of each class."""
        def default(self, obj):
            if isinstance(obj, _JsonAble):
                return obj.encode()
            elif type(obj) == np.float32:
                return float(obj)
            else:
                return json.JSONEncoder(ensure_ascii=False).default(obj)


class DictCoder:
    def __init__(self):
        self._hr = HookReg()  #This keeps track of the various deserialization hooks and combines them. pass _hr.getHook() to the json.load function.

    def registerClass(self, cls: typing.Type[Dictable]):
        self._hr.addHook(cls.fromDict)

    def dictDecode(self, d):
        if isinstance(d, (int, float, bool, str)):
            pass
        elif isinstance(d, list):
            for i, e in enumerate(d):
                d[i] = self.dictDecode(e)
        elif isinstance(d, dict):
            for k, v in d.items():
                d[k] = self.dictDecode(v)
        else:
            return d
        d = self._hr.getHook()(d)
        return d


class Dictable(abc.ABC):
    """Base class for converting PropertyMap objects to simpler dictionary trees, more simiular to traditional JSON."""
    @abc.abstractmethod
    def _toDict(self):
        pass

    @staticmethod
    @abc.abstractmethod
    def fromDict(d):
        pass

    def toDict(self):
        return Dictable._dictEncode(self._toDict())

    @staticmethod
    def _dictEncode(d):
        if isinstance(d, list):
            D = []
            for i in d:
                D.append(Dictable._dictEncode(i))
            return D
        elif isinstance(d, dict):
            D = {}
            for k, v in d.items():
                D[k] = Dictable._dictEncode(v)
            return D
        elif isinstance(d, Dictable):
            return Dictable._dictEncode(d._toDict())
        else:
            return d


@dataclass
class Property(_JsonAble, Dictable):
    """Represents a single property from a micromanager PropertyMap

    Attributes:
        pType: The type of the property. may be 'STRING', 'DOUBLE', or 'INTEGER'
        value: The value of the propoerty. Should match the type given in `pType`
    """
    pType: str
    value: typing.Union[str, int, float, typing.List[typing.Union[str, int, float]]]
    pTypes = {str: 'STRING', float: 'DOUBLE', int: 'INTEGER'}

    def encode(self) -> dict:
        d = {'type': self.pType}
        if isinstance(self.value, list):
            d['array'] = self.value
        else:
            d['scalar'] = self.value
        return d

    @staticmethod
    def hook(d: dict):
        if 'type' in d and d['type'] in Property.pTypes.values():

            if 'array' in d:
                val = d['array']
            elif 'scalar' in d:
                val = d['scalar']
            else:
                return d
            return Property(pType=d['type'], value=val)
        else:
            return d

    def _toDict(self):
        return self.value

    @staticmethod
    def fromDict(d):
        if isinstance(d, (int, float, str)):
            return Property(Property.pTypes[type(d)], d)
        elif isinstance(d, list):
            if all([isinstance(i, Property) for i in d]):
                return Property(d[0].pType, [i.value for i in d])
        return d


@dataclass
class PropertyMap(_JsonAble, Dictable):
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

    def _toDict(self):
        return self.properties

    @staticmethod
    def fromDict(d):
        if isinstance(d, list):
            if all([isinstance(i, PropertyMap) for i in d]):
                return PropertyMap([i.properties for i in d])
        if isinstance(d, dict):
            if all([isinstance(i, (PropertyMap, Property)) for i in d.values()]):
                return PropertyMap(d)
        return d


@dataclass
class PropertyMapFile(_JsonAble, Dictable):
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

    def _toDict(self):
        return {"map": {self.mapName: self.pMap}}

    @staticmethod
    def fromDict(d):
        if isinstance(d, PropertyMap):
            if 'map' in d.properties:
                if isinstance(d.properties['map'], PropertyMap):
                    k, v = next(iter(d.properties['map']))
                    return PropertyMapFile(mapName=k, pMap=v)
        return d

    @staticmethod
    def loadFromFile(path: str):
        with open(path) as f:
            return json.load(f, object_hook=_JsonAble._hr.getHook())

    def saveToFile(self, path: str):
        with open(path, 'w') as f:
            json.dump(self, f, cls=_JsonAble._Encoder, indent=2)


_JsonAble.registerClass(Property)
_JsonAble.registerClass(PropertyMapFile)
_JsonAble.registerClass(PropertyMap)

coder = DictCoder()
coder.registerClass(Property)
coder.registerClass(PropertyMap)
coder.registerClass(PropertyMapFile)

if __name__ == '__main__':
    path1 = r'C:\Users\nicke\Desktop\PositionList3.pos'
    path2 = r'C:\Users\nicke\Desktop\PositionList4.pos'
    p = PropertyMapFile.loadFromFile(path1)
    p.saveToFile(path2)
    with open(path1) as f1, open(path2) as f2:
        assert f1.read() == f2.read()
    a = p.toDict()
    b = coder.dictDecode(a)
    a = 1