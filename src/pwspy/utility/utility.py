# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 11:31:48 2018

@author: backman05
"""
import multiprocessing as mp
import queue
import threading as th
import typing
from time import time
from typing import Union

import psutil
from pwspy import ImCube
from pwspy.imCube.ICMetaDataClass import ICMetaData

'''Local Functions'''


def _recursiveSearch(fileDict, specifierNames, specifiers: typing.List[str] = None):
    if specifiers is None:
        specifiers = []
    results = []
    if isinstance(fileDict, dict):
        for k, v in fileDict.items():
            results.extend(_recursiveSearch(v, specifierNames, specifiers + [k]))
    elif isinstance(fileDict, (list, tuple)):
        for file in fileDict:
            fileSpecifiers = specifiers
            if specifierNames is None:
                results.append(({'specifiers': fileSpecifiers}, file))
            else:
                results.append((dict(zip(specifierNames, fileSpecifiers)), file))
    else:
        raise TypeError(f'Filedict must only contain Dict and List[str], not an item of type: {type(fileDict)}')
    return results


def _loadIms(qout, qin, lock):
    while not qin.empty():
        specs, file = qin.get()
        print('starting', file)
        im = ImCube.loadAny(file, lock=lock)
        for k, v in specs.items():
            setattr(im, k, v)
        qout.put(im)
        perc = psutil.virtual_memory().percent
        print(file)
        print("Memory Usage: ", perc, '%')
        if perc >= 95:
            print('quitting')
            return


def _loadThenProcess(procFunc, procFuncArgs, lock, fileAndSpecifiers):
    specs, file = fileAndSpecifiers
    if isinstance(file, str):
        im = ImCube.loadAny(file, lock=lock)
    elif isinstance(file, ICMetaData):
        im = ImCube.fromMetadata(file, lock=lock)
    else:
        raise TypeError("files specified to the loader must be either str or ICMetaData")
    for k, v in specs.items():
        setattr(im, k, v)
    print("Run", file)
    return procFunc(im, *procFuncArgs)


'''User Functions'''


def loadAndProcess(fileDict: Union[dict, list], processorFunc=None, specifierNames: list = None, parallel=False, procArgs=None) -> \
        typing.List[ImCube]:
    if procArgs is None:
        procArgs = []
    # Error checking
    numThreads = 2  # even this might be unnecesary. don't bother going higher.
    print("Starting loading")
    if specifierNames is not None:
        recursionDepth = 0
        fileStructure = fileDict
        while not isinstance(fileStructure, list):
            fileStructure = fileStructure[list(fileStructure.keys())[0]]
            recursionDepth += 1
        if recursionDepth != len(specifierNames):
            raise ValueError(
                "The length of specifier names does not match the number of layers of folders in the fileDict")
    sTime = time()
    files = _recursiveSearch(fileDict, specifierNames)
    print(f'found {len(files)} files')
    if parallel:
        if processorFunc is None:
            raise Exception("Running in parallel with no processorFunc is a bad idea.")
        m = mp.Manager()
        lock = m.Lock()
        po = mp.Pool(processes=psutil.cpu_count(logical=False) - 1)
        try:
            cubes = po.starmap(_loadThenProcess, zip(*zip(*[[processorFunc, procArgs, lock]] * len(files)), files))
        finally:
            po.close()
    else:
        qout = queue.Queue()
        qin = queue.Queue()
        [qin.put(f) for f in files]
        lock = th.Lock()
        threads = [th.Thread(target=_loadIms, args=[qout, qin, lock]) for i in range(numThreads)]
        [thread.start() for thread in threads]
        print('threads started')
        if processorFunc is not None:
            cubes = [processorFunc(qout.get(), *procArgs) for i in range(len(files))]
        else:
            cubes = [qout.get() for i in range(len(files))]
        [thread.join() for thread in threads]
    print(f"Loading took {time() - sTime} seconds")
    return cubes
