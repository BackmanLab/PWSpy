# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 11:31:48 2018

@author: backman05
"""
from pwspy import ImCube
import numpy as np
import psutil
import multiprocessing as mp
import threading as th
import typing
import os
from time import time
import sys
import queue

'''Local Functions'''
def _recursiveSearch(fileDict, specifierNames, specifiers:typing.List[str]=[]):
    results = []
    if isinstance(fileDict,dict):
        for k,v in fileDict.items():
            results.extend(_recursiveSearch(v,specifiers + [k]))
    elif isinstance(fileDict,list):
        for file in fileDict:
            fileSpecifiers = specifiers
            if specifierNames is None:
                results.append(({'specifiers':fileSpecifiers}, file))
            else:
                results.append((dict(zip(specifierNames, fileSpecifiers)), file))
    else:
        raise TypeError(f'Filedict must only contain Dict and List[str], not an item of type: {type(arg)}')
    return results

def _loadIms(qout, qin, lock):
    while not qin.empty():
        specs, file = qin.get()
        print('starting',file)
        lock.acquire()
        im = ImCube.loadAny(file)
        lock.release()
        for k,v in specs.items():
            setattr(im, k, v)
        qout.put(im)
        perc = psutil.virtual_memory().percent
        print(file)
        print("Memory Usage: ", perc,'%')
        if perc >= 95:
            print('quitting')
            return
        
def loadThenProcess(procFunc,procFuncArgs, lock, fileAndSpecifiers):
    specs, file = fileAndSpecifiers
    lock.acquire()
    im = ImCube.loadAny(file)
    lock.release()
    for k,v in specs.items():
        setattr(im, k, v)
    print("Run", file)
    return procFunc(im, *procFuncArgs)

'''User Functions'''
def loadAndProcess(fileDict:dict, processorFunc = None, specifierNames:list = None, parallel = False, procArgs = []) -> typing.List[ImCube]:
    #Error checking
    numThreads = 2 #even this might be unnecesary. don't bother going higher.
    print("Starting loading")
    if not specifierNames is None:
        recursionDepth = 0
        fileStructure = fileDict
        while not isinstance(fileStructure, list):
            fileStructure = fileStructure[list(fileStructure.keys())[0]]
            recursionDepth += 1
        if recursionDepth != len(specifierNames):
            raise ValueError("The length of specifier names does not match the number of layers of folders in the fileDict")
    sTime = time()
    files = _recursiveSearch(fileDict, specifierNames)
    print(f'found {len(files)} files')
#    numIms = len(files)
    if parallel:
        if processorFunc is None:
            raise Exception("Running in parallel with no processorFunc is a bad idea.")
        m = mp.Manager()
        lock = m.Lock()
        po = mp.Pool(processes = psutil.cpu_count(logical=False)-1)
        cubes = po.starmap(loadThenProcess, zip(*zip(*[[processorFunc, procArgs, lock]]*len(files)), files))
    else:
        qout = queue.Queue()
        qin = queue.Queue()
        [qin.put(f) for f in files]
        lock = th.Lock()
#        thread1 = th.Thread(target = _loadIms, args=[qout, qin, lock])
#        thread2 = th.Thread(target = _loadIms, args=[qout, qin, lock])
#        thread1.start()
#        thread2.start()
        threads = [th.Thread(target = _loadIms, args = [qout, qin, lock]) for i in range(numThreads)]
        [thread.start() for thread in threads]
        print('threads started')
        if processorFunc is not None:
            cubes = [processorFunc(qout.get(),*procArgs) for i in range(len(files))]
        else:
            cubes = [qout.get() for i in range(len(files))]
#        thread1.join()
#        thread2.join()
        [thread.join() for thread in threads]
    print(f"Loading took {time()-sTime} seconds")
    return cubes


