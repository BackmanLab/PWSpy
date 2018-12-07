# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 17:53:24 2018

@author: backman05
"""
from __future__ import annotations
import json
import typing
import numpy as np
import copy


class Property:
    '''Represents a single property from a micromanager PropertyMap'''
    def __init__(self, name:str, pType:str, value):
        self.name = name
        assert pType in ['STRING','DOUBLE','INTEGER']
        self._d = {'type': pType}
        if isinstance(value, list):
            self._d['array'] = value
        else:
            self._d['scalar'] = value

class PropertyMap:
    '''Represents a propertyMap from micromanager. basically a list of properties.'''
    def __init__(self,name:str, properties:typing.List[Property]):
        self.properties = properties
        self.name = name
        if isinstance(properties[0], Property):
            self._d = {'type':'PROPERTY_MAP',
                      'array': [{i.name:i for i in self.properties}]}
        elif isinstance(properties[0], Position2d):
            self._d = {'type':'PROPERTY_MAP',
                      'array': [i._d for i in self.properties]}
        else:
            raise TypeError
            
class Position2d:
    '''Represents a position for a single xy stage in micromanager.'''
    def __init__(self, x:float, y:float, xyStage:str='', label:str=''):
        self.x = x
        self.y = y
        self.xyStage = xyStage
        self.label = label
        self._regen()
    def _regen(self):
        contents = [
            Property("DefaultXYStage", "STRING", self.xyStage),
            Property("DefaultZStage", "STRING", ""),
            PropertyMap("DevicePositions",
                        [Property("Device", "STRING", self.xyStage),
                        Property("Position_um", "DOUBLE", [self.x, self.y])]),
            Property("GridCol", "INTEGER", 0),
            Property("GridRow", "INTEGER", 0),
            Property("Label", "STRING",self.label)]
        self._d = {i.name:i for i in contents}      
    def mirrorX(self):
        self.x *= -1
        self._regen()
    def mirrorY(self):
        self.y *= -1
        self._regen()  
    def renameStage(self, newName):
        self.xyStage = newName
        self._regen()      
    def __repr__(self):
        return f"Position2d({self.xyStage}, {self.x}, {self.y})"  
    def __add__(self, other:'Position2d')->'Position2d':
        assert isinstance(other, Position2d)
        return Position2d(self.x + other.x,
                          self.y + other.y,
                          self.xyStage,
                          self.label)       
    def __sub__(self, other:Position2d)->Position2d:
        assert isinstance(other, Position2d)
        return Position2d(self.x - other.x,
                          self.y - other.y,
                          self.xyStage,
                          self.label)
        
class PositionList:
    '''Represents a micromanager positionList. can be loaded from and saved to a micromanager .pos file.'''
    def __init__(self, positions: typing.List[Position2d]):
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
    def copy(self) -> PositionList:
        return copy.deepcopy(self)
    def save(self, savePath:str):
        #    a=json.dumps(plist,cls=Encoder, ensure_ascii=False)
        #    a = a.replace('{','{\n').replace('[','[\n').replace('}','\n}').replace(',',',\n').replace(']','\n]')
        if savePath[-4:] != '.pos':
            savePath += '.pos'
        with open(savePath,'w') as f:
            json.dump(self,f,cls=PositionList.Encoder)
    @classmethod
    def load(cls, filePath:str) -> PositionList:
        def _decode(dct):
            if 'format' in dct:
                if dct['format'] == 'Micro-Manager Property Map' and int(dct['major_version'])==2:
                    positions=[]
                    for i in dct['map']['StagePositions']['array']:
                        label = i['Label']['scalar']
                        xyStage = i["DefaultXYStage"]['scalar']
                        coords = i["DevicePositions"]['array'][0]["Position_um"]['array']
                        positions.append(Position2d(*coords, xyStage, label))
            else:
                return dct
                raise TypeError("Not Recognized")
            return PositionList(positions)
        with open(filePath,'r') as f:
            return json.load(f, object_hook=_decode)
    def __repr__(self):
        s = "PositionList(\n["
        for i in self.positions:
            s += str(i) + '\n'
        s += '])'
        return s  
    def __add__(self, other:Position2d) -> Position2d:
        assert isinstance(other, Position2d)
        return PositionList([i + other for i in self.positions])     
    def __sub__(self, other:Position2d) -> Position2d:
        assert isinstance(other, Position2d)
        return PositionList([i - other for i in self.positions])      
    class Encoder(json.JSONEncoder):
        '''Allows for the position list and related objects to be jsonified.'''
        def default(self,obj):
            if isinstance(obj, (PositionList, Position2d, PropertyMap, Property)):
                return obj._d
            else:
                return json.JSONEncoder(ensure_ascii=False).default(self, obj)
    def __len__(self):
        return len(self.positions)
    def __getitem__(self,idx:slice):
        return self.positions[idx]
    
if __name__ == '__main__':

    def generateList(data:np.ndarray):
        assert isinstance(data,np.ndarray)
        assert len(data.shape)==2
        assert data.shape[1]==2
        positions=[]
        for n,i in enumerate(data):
            positions.append(Position2d(*i,'TIXYDrive',f'Cell{n+1}'))
        plist = PositionList(positions)
        return plist
    
    def pws1to2(loadPath,newOriginX, newOriginY):
        pws1 = PositionList.load(loadPath)
        pws2 = pws1.copy()
        pws2.mirrorX()
        pws2.mirrorY()
        pws2Origin = Position2d(newOriginX, newOriginY)
        offset = pws2Origin - pws2.positions[0]
        pws2 = pws2 + offset
        pws2.renameStage("TIXYDrive")
        return pws2
    
    def pws1toSTORM(loadPath,newOriginX, newOriginY):
        pws1 = PositionList.load(loadPath)
        pws2 = pws1.copy()
        pws2.mirrorY()
        pws2Origin = Position2d(newOriginX, newOriginY)
        offset = pws2Origin - pws2.positions[0]
        pws2 = pws2 + offset
        pws2.renameStage("TIXYDrive")
        return pws2