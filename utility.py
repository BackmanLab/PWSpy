# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 11:31:48 2018

@author: backman05
"""
from pwspython import ImCube
import psutil
import multiprocessing as mp
import threading as th
import typing


def _loadIms(q, fileDict, specifierNames):
        def a(arg, specifiers:typing.List[str] = []):
            if isinstance(arg,dict):
                for k,v in arg.items():
                    a(v,specifiers + [k])
            elif isinstance(arg,list):
                for file in arg:
                    _ =ImCube.loadAny(file)
                    if specifierNames is None:
                        _.specifiers = specifiers
                    else:
                        for i,name in enumerate(specifierNames):
                            setattr(_,name,specifiers[i])
                    _.exposure = _.metadata['exposure']
                    q.put(_)
                    perc = psutil.virtual_memory().percent
                    print(file)
                    print("Memory Usage: ", perc,'%')
                    if perc >= 95:
                        del cubes
                        print('quitting')
                        quit()  
            else:
                raise TypeError(f'Filedict must only contain Dict and List, not an item of type: {type(arg)}')
        a(fileDict)

def loadAndProcess(fileDict:dict, processorFunc = None, specifierNames:list = None, parallel = False):
    numIms = 0
    for i, v in fileDict.items():
        for j, lis in v.items():
            numIms += len(lis)
    m = mp.Manager()
    q = m.Queue()
    thread = th.Thread(target = _loadIms, args=[q, fileDict, specifierNames])
    thread.start()

    if processorFunc is not None:
        #%% Start processing
        if parallel:
            po = mp.Pool(processes = psutil.cpu_count(logical=False)-1)
            cubes = po.map(processorFunc, [q]*numIms)
        else:
            cubes = [processorFunc(q) for i in range(numIms)]
        thread.join()
    else:
        cubes = [q.get() for i in range(numIms)]
    return cubes