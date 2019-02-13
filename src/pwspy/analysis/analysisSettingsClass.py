# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 21:33:29 2019

@author: Nick
"""
from typing import NamedTuple
import json

class AnalysisSettings(NamedTuple):
    filterOrder:int
    filterCutoff:float
    polynomialOrder:int
    rInternalSubtractionPath:str
    referenceMaterial:str
    wavelengthStart:int
    wavelengthStop:int
    useHannWindow:bool
    autoCorrStopIndex:int
        
        
    @classmethod
    def fromJson(cls, filePath):
        with open(filePath,'r') as f:
            return cls(**json.load(f))
        
    def toJson(self,filePath):
        with open(filePath,'w') as f:
            json.dump(dict(self),f)
                    