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
from typing import Union, Optional

import psutil
from pwspy import ImCube
from pwspy.imCube.ICMetaDataClass import ICMetaData

'''Local Functions'''


def _recursiveSearch(fileDict, specifierNames, specifiers: typing.List[str] = None):
    """This function crawls through the nested dictionary of fileDict and provides a list of each filePath coupled
    with a tuple of its specifiers. On the initial call `specifiers` should be left blank. As the function recursively
    calls itself it will populate this variable with its search results so far."""
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
    """When not running in parallel this function is executed in a separate thread to load ImCubes and populate a Queue
    with them."""
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
    """Handles loading the ImCubes from file and if needed then calling the processorFunc. This function will be executed
     on each core when running in parallel. If not running in parallel then _loadIms will be used."""
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


def loadAndProcess(fileDict: Union[dict, list], processorFunc: Optional = None, specifierNames: typing.List[str] = None,
                   parallel: Optional=False, procArgs: Optional = None) -> typing.List[typing.Any]:
    """    A convenient function to load a series of ImCubes from a list or dictionary of file paths.

    Parameters
    ----------
    fileDict
        A nested dictionary where the end point of each dictionary is a list of ImCube file paths. If no specifiers are used this
         can just be a list of file paths. The dictionary keys should be the specifiers for the corresponding item of
         specifier names. e.g. if specifierNames is ['material', 'date'] then the fileDict might look like:
         {'water':{ '20-3-2019': ['path1', 'path2'], '21-3-2019': ['path3', 'path4']}}
    processorFunc
        A function that each loaded cell should be passed to. The first argument of processorFunc should be the loaded
        ImCube. Additional arguments can be passed to processorFunc using the procArgs variable.
    specifierNames
        a list of strings describing what parameter the keys at each level of the fileDict dictionary describe. Each
        loaded ImCube will have the specifiersNames added as attributes. e.g. using the fileDict example, the ImCube for
        'path1' would have an attribute material = 'water' and an attribute date = '20-3-2019'
    parallel
        default is False. If True then the loading and processing will be performed in parallel on multiple cores,
        otherwise it will be done using multithreading on a single core. Setting this to true can result if big speedups
        if the time to run processorFunc is greater than the time to load an ImCube from file.
    procArgs
        Optional arguments to pass to processorFunc

    Returns
    -------
    list
        If not using processorFunc a list of ImCubes will be returned. Otherwise a list of the return values from
        processorFunc will be returned.

    """
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
