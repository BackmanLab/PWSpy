# -*- coding: utf-8 -*-
"""
Created on Wed Aug 22 11:05:40 2018

@author: Nick
"""

import pandas as pd
import numpy as np
import os

def _init():
    fileLocation = os.path.join(os.path.split(__file__)[0], 'refractiveIndexFiles')
    ser = {}    # a dictionary of the series by name
    for name,file in materials.items():
        #create a series for each csv file
        arr = np.genfromtxt(os.path.join(fileLocation,file),skip_header=1,delimiter=',')
        _ = pd.DataFrame({'n':arr[:,1], 'k':arr[:,2]},index=arr[:,0].astype(np.float)*1e3)
        ser[name] = _
    
    #Find the first and last indices that won't require us to do any extrapolation
    first = []
    last = []
    for k,v in ser.items():
        first += [v.first_valid_index()]
        last += [v.last_valid_index()]
    first  = max(first)
    last = min(last)
    #Interpolate so we don't have any nan values.
#    df = pd.DataFrame(ser)
    df = pd.concat(ser, axis='columns')
    df = df.interpolate('index')
    n = df.loc[first:last]
    return n

materials = {
        'glass': 'N-BK7.csv',
        'water': 'Daimon-21.5C.csv',
        'air': 'Ciddor.csv',
        'silicon': 'Silicon.csv'}
n = _init()
del  _init

def getReflectance(mat1: str, mat2: str, index = None):
    '''Given the names of two interfaces this provides the reflectance in units of percent.
    If given a series as index the data will be interpolated and reindexed to match the index.'''
    nc1 = np.array([np.complex(i[0],i[1]) for idx, i in n[mat1].iterrows()])    #complex index for material 1
    nc2 = np.array([np.complex(i[0],i[1]) for idx, i in n[mat2].iterrows()]) 
    result = np.abs(((nc1 - nc2) / (nc1 + nc2))**2) * 100
    result = pd.Series(result, index=n.index)
    if index is not None:
        index = pd.Index(index)
        combinedIdx = result.index.append(index)    #An index that contains all the original index points and all of the new. That way we can interpolate without first throwing away old data.
        result = result.reindex(combinedIdx)
        result = result.sort_index()
        result = result.interpolate()
        result = result[~result.index.duplicated()] #remove duplicate indices to avoid error
        result = result.reindex(index)  #reindex again to get rid of unwanted index points.
    return result
        
r= getReflectance('air','silicon')