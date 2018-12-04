# -*- coding: utf-8 -*-
"""
Created on Mon Dec  3 17:53:24 2018

@author: backman05
"""

import json
import typing

class Property:
    def __init__(self, name:str, pType:str, value):
        self.name = name
        assert pType in ['STRING','DOUBLE','INTEGER']
        self._d = {'type': pType}
        if isinstance(value, list):
            self._d['array'] = value
        else:
            self._d['scalar'] = value

class PropertyMap:
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
    def __init__(self, x:float, y:float, xyStage:str, label:str):
        self.x = x
        self.y = y
        contents = [
                Property("DefaultXYStage", "STRING", xyStage),
                Property("DefaultZStage", "STRING", ""),
                PropertyMap("DevicePositions",
                            [Property("Device", "STRING", xyStage),
                            Property("Position_um", "DOUBLE", [self.x, self.y])]),
                Property("GridCol", "INTEGER", 0),
                Property("GridRow", "INTEGER", 0),
                Property("Label", "STRING",label)]
        self._d = {i.name:i for i in contents}
        
    def mirrorX(self):
        self.x *= -1
    def mirrorY(self):
        self.y *= -1
    def addOffset(self, dx, dy):
        self.x += dx
        self.y += dy
    
class PositionList:
    def __init__(self, positions: typing.List[Position2d]):
        self.positions = positions
        self._d = {"encoding": "UTF-8",
                   'format': 'Micro-Manager Property Map',
                   'major_version': 2,
                   'minor_version': 0,
                   "map": {"StagePositions": PropertyMap("StagePositions", self.positions)}}
    def mirrorX(self):
        for i in self.positions:
            i.mirrorX()
    def mirrorY(self):
        for i in self.positions:
            i.mirrorY()
    def addOffset(self, dx, dy):
        for i in self.positions:
            i.addOffset(dx, dy)
            
class Encoder(json.JSONEncoder):
    def default(self,obj):
#        if isinstance(obj, set):
#            st = '{'
#            for i in obj:
#                st += json.dumps(i, cls=Encoder, ensure_ascii=False) + ','
#            st += '}'
#            return st
        if isinstance(obj, PositionList):
            return obj._d
        elif isinstance(obj, Position2d):
            return obj._d
        elif isinstance(obj, PropertyMap):
            return obj._d
        elif isinstance(obj, Property):
            return obj._d#obj.name+':'+json.dumps(obj._d, cls=Encoder, ensure_ascii=False)
        else:
            return json.JSONEncoder(ensure_ascii=False).default(self, obj)
    
if __name__ == '__main__':
#    p=Property('hey','STRING','323')
#    p2 = PropertyMap('hah',[p])
#    pos = Position2d(1,2,'re','rara')
#    a = json.dumps(pos,cls=Encoder)
    pos=[[0,0],
     [1,1],
     [2,3]]
    
    positions=[]
    for n,i in enumerate(pos):
        positions.append(Position2d(*i,'XY',str(n)))
    plist = PositionList(positions)
    a=json.dumps(plist,cls=Encoder, ensure_ascii=False)
    a = a.replace('{','{\n').replace('[','[\n').replace('}','\n}').replace(',',',\n').replace(']','\n]')