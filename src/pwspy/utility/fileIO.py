# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 11:31:48 2018

@author: Nick Anthony
"""
import multiprocessing as mp
import queue
import threading as th
from time import time
from typing import Union, Optional, List, Tuple
import pandas as pd
import psutil
from pwspy.dataTypes import ICMetaData, AcqDir
from pwspy.dataTypes.metadata import MetaDataBase

'''Local Functions'''
def _load(loadHandle: Union[str, MetaDataBase], lock: mp.Lock):
    md: MetaDataBase
    if isinstance(loadHandle, str):
        md = AcqDir(loadHandle).pws # In the case that we just have a string to work with, we assume that we are loading a PWS file and not any other type such as dynamics.
    elif isinstance(loadHandle, MetaDataBase):
        md = loadHandle
    else:
        raise TypeError("files specified to the loader must be either str or inherited from pwspy.dataTypes.MetaDataBase")
    return md.toDataClass(lock)


def _loadIms(qout: queue.Queue, qin: queue.Queue, lock: th.Lock):
    """When not running in parallel this function is executed in a separate thread to load ImCubes and populate a Queue
    with them."""
    while not qin.empty():
        try:
            index, row = qin.get()
            displayStr = row['cube'].filePath if isinstance(row['cube'], MetaDataBase) else row['cube']
            print('Starting', displayStr)
            im = _load(row['cube'], lock=lock)
            row['cube'] = im
            qout.put((index, row))
            perc = psutil.virtual_memory().percent
            print("Memory Usage: ", perc, '%')
            if perc >= 95:
                print('quitting')
                return
        except Exception as e:
            qout.put(e) #Put the error in the queue so it can propagate to the main thread.
            raise e

def _procWrap(procFunc, lock: th.Lock):
    def func(fromQueue, procFuncArgs=None):
        index, row = fromQueue
        im = row['cube']
        args = (im,)
        if procFuncArgs:
            ret = procFunc(*args, *procFuncArgs)
        else:
            ret = procFunc(*args)
        row['cube'] = ret
        return index, row
    return func


def _loadThenProcess(procFunc, procFuncArgs, lock: mp.Lock, row):
    """Handles loading the ImCubes from file and if needed then calling the processorFunc. This function will be executed
     on each core when running in parallel. If not running in parallel then _loadIms will be used."""
    index, row = row
    im = _load(row['cube'], lock=lock)
    displayStr = row['cube'].filePath if isinstance(row['cube'], MetaDataBase) else row['cube']
    print("Run", displayStr, mp.current_process())
    ret = procFunc(im, *procFuncArgs)
    row['cube'] = ret
    return row


'''User Functions'''


def loadAndProcess(fileFrame: Union[pd.DataFrame, List, Tuple], processorFunc: Optional = None, parallel: Optional = None,
                   procArgs: Optional = None, initializer=None,
                   initArgs=None) -> Union[pd.DataFrame, List, Tuple]:
    """DEPRECATED! This over-complicated function should be replaced with usage of processParallel.
    A convenient function to load a series of Data Cubes from a list or dictionary of file paths.

    Parameters
    ----------
    fileFrame
        A dataframe containing a column of ImCube file paths titled 'cube' and other columns to act as specifiers for each cube.
        If no specifiers are used this can just be a list of file paths.
    processorFunc
        A function that each loaded cell should be passed to. The first argument of processorFunc should be the loaded
        ImCube. Additional arguments can be passed to processorFunc using the procArgs variable.
    parallel
        default is `False`. If `True` then the loading and processing will be performed in parallel on multiple cores,
        otherwise it will be done using multithreading on a single core. Setting this to true can result if big speedups
        if the time to run processorFunc is greater than the time to load an ImCube from file.
    procArgs
        Optional arguments to pass to processorFunc
    initializer:
        A function that is run once at the beginning of each spawned process. Can be used for copying shared memory.
    initArgs:
        A tuple of arguments to pass to the `initializer` function.

    Returns
    -------
    Dataframe or list
        returns an object of the same form as fileFrame except the ImCube file paths have been replaced by ImCube Object.
        If using processorFunc the return values from processorFunc will be returned rather than ImCube Objects.
    """
    if procArgs is None:
        procArgs = []
    if parallel is None:
        parallel = False if processorFunc is None else True  # No reason to run in parallel if we don't have a computationally expensive function to run.
    #If the fileFrame provided is not already a pandas dataframe the convert and store a reference to the original type. We'll try to convert back at the end.
    origClass = None
    if not isinstance(fileFrame, pd.DataFrame):
        try:
            origClass = type(fileFrame)
            fileFrame = pd.DataFrame({'cube': fileFrame})
        except:
            raise TypeError("fileFrame cannot be converted to a pandas dataframe")
    # Error checking
    if 'cube' not in fileFrame.columns:
        raise IndexError("The fileFrame must contain a 'cube' column.")
    print(f"Starting loading {len(fileFrame)} files.")
    sTime = time()
    if parallel:
        if processorFunc is None:
            raise Exception("Running in parallel with no processorFunc is pointles. Set parallel to False to run in multithreaded mode.")
        m = mp.Manager()
        lock = m.Lock()
        numProcesses = psutil.cpu_count(logical=False) - 1  # Use one less than number of available cores.
        po = mp.Pool(processes=numProcesses, initializer=initializer, initargs=initArgs)
        try:
            cubes = po.starmap(_loadThenProcess, zip(*zip(*[[processorFunc, procArgs, lock]] * len(fileFrame)), fileFrame.iterrows()))
        finally:
            po.close()
            po.join()
    else:
        if initializer:
            initializer(*initArgs)
        qout = queue.Queue()
        qin = queue.Queue()
        [qin.put(f) for f in fileFrame.iterrows()]
        lock = th.Lock()
        thread = th.Thread(target=_loadIms, args=[qout, qin, lock])
        thread.start()
        cubes = []
        if processorFunc:
            wrappedFunc = _procWrap(processorFunc, lock)
        for i in range(len(fileFrame)):
            ret = qout.get()
            if isinstance(ret, Exception):
                raise ret
            else:
                if processorFunc:
                    cubes.append(wrappedFunc(ret, procArgs))
                else:
                    cubes.append(ret)  # A list of tuples of index, dataframe row
        thread.join()
        indices, cubes = zip(*sorted(cubes)) #This ensures that the return value is in the same order as the input array.
    print(f"Loading took {time() - sTime} seconds")
    ret = pd.DataFrame(list(cubes))
    if origClass is None:
        return ret
    else:
        return origClass(ret['cube'])


def processParallel(fileFrame: pd.DataFrame, processorFunc, initializer=None, initArgs=None, procArgs=None):
    """A convenient function to load a series of Data Cubes from a list or dictionary of file paths.

    Parameters
    ----------
    fileFrame
        A dataframe. Each row of the frame will be passed as the first argument to the processorFunc.
    processorFunc
        A function that each row of the `fileFrame` should be passed to as the first argument. Additional arguments can be passed to processorFunc using the procArgs variable.
    procArgs
        Optional arguments to pass to processorFunc
    initializer:
        A function that is run once at the beginning of each spawned process. Can be used for copying shared memory.
    initArgs:
        A tuple of arguments to pass to the `initializer` function.

    Returns
    -------
    list
        returns an list containing the results each execution of processorFun.
    """
    numProcesses = psutil.cpu_count(logical=False) - 1  # Use one less than number of available cores.
    po = mp.Pool(processes=numProcesses, initializer=initializer, initargs=initArgs)
    try:
        vars = fileFrame.iterrows() if procArgs is None else zip(fileFrame.iterrows(), *zip(*[[procArgs]] * len(fileFrame)))
        cubes = po.starmap(processorFunc, vars)
    finally:
        po.close()
        po.join()
    return cubes