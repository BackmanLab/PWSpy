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
from pwspy.dataTypes import ICMetaData, ImCube, MetaDataBase

'''Local Functions'''


def _load(loadHandle: Union[str, MetaDataBase], metadataOnly: bool, lock: mp.Lock):
    md: MetaDataBase
    if isinstance(loadHandle, str):
        md = ICMetaData.loadAny(loadHandle, lock=lock)  # In the case that we just have a string to work with, we assume that we are loading a PWS file and not any other type such as dynamics.
    elif isinstance(loadHandle, MetaDataBase):
        md = loadHandle
    else:
        raise TypeError("files specified to the loader must be either str or ICMetaData")
    if metadataOnly:
        return md
    else:
        return md.toDataClass(lock)


def _loadIms(qout: queue.Queue, qin: queue.Queue, metadataOnly: bool, lock: th.Lock):
    """When not running in parallel this function is executed in a separate thread to load ImCubes and populate a Queue
    with them."""
    while not qin.empty():
        try:
            index, row = qin.get()
            displayStr = row['cube'].filePath if isinstance(row['cube'], MetaDataBase) else row['cube']
            print('Starting', displayStr)
            im = _load(row['cube'], metadataOnly=metadataOnly, lock=lock)
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

def _procWrap(procFunc, passLock: bool, lock: th.Lock):
    def func(fromQueue, procFuncArgs=None):
        index, row = fromQueue
        im = row['cube']
        if passLock:
            args = (im, lock)
        else:
            args = (im,)
        if procFuncArgs:
            ret = procFunc(*args, *procFuncArgs)
        else:
            ret = procFunc(*args)
        row['cube'] = ret
        return index, row
    return func


def _loadThenProcess(procFunc, procFuncArgs, metadataOnly: bool, lock: mp.Lock, passLock: bool, row):
    """Handles loading the ImCubes from file and if needed then calling the processorFunc. This function will be executed
     on each core when running in parallel. If not running in parallel then _loadIms will be used."""
    index, row = row
    im = _load(row['cube'], metadataOnly=metadataOnly, lock=lock)
    displayStr = row['cube'].filePath if isinstance(row['cube'], MetaDataBase) else row['cube']
    print("Run", displayStr, mp.current_process())
    if passLock:
        ret = procFunc(im, lock, *procFuncArgs)
    else:
        ret = procFunc(im, *procFuncArgs)
    row['cube'] = ret
    return row


'''User Functions'''


def loadAndProcess(fileFrame: Union[pd.DataFrame, List, Tuple], processorFunc: Optional = None, parallel: Optional=None,
                   procArgs: Optional = None, metadataOnly: bool = False, passLock: bool = False, initializer=None,
                   initArgs=None, maxProcesses: int = 1000) -> Union[pd.DataFrame, List, Tuple]:
    """A convenient function to load a series of ImCubes from a list or dictionary of file paths.

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
    metadataOnly:
        Instead of passing an ImCube or DynCube object to the first argument of processorFunc, pass the MetaData object
    passLock:
        If true then pass the multiprocessing lock object to the second argument fo processorFunc. this can be used to
        synchronize hard disk activity.
    initializer:
        A function that is run once at the beginning of each spawned process. Can be used for copying shared memory.
    initArgs:
        A tuple of arguments to pass to the `initializer` function.
    maxProcesses:
        The maximum number of processes that can be spawned. Regardless of this parameter the function will not spawn more
        than 1 less than the total number of cores on the cpu.

    Returns
    -------
    Dataframe or list
        returns an object of the same form as fileFrame except the ImCube file paths have been replaced by ImCube Object.
        If using processorFunc the return values from processorFunc will be returned rather than ImCube Objects.
    """
    if procArgs is None:
        procArgs = []
    if parallel is None:
        if processorFunc is None: parallel = False
        else: parallel = True
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
            raise Exception("Running in parallel with no processorFunc is a bad idea.")
        m = mp.Manager()
        lock = m.Lock()
        numProcesses = min([psutil.cpu_count(logical=False) - 1, maxProcesses])
        po = mp.Pool(processes=numProcesses, initializer=initializer, initargs=initArgs)
        try:
            cubes = po.starmap(_loadThenProcess, zip(*zip(*[[processorFunc, procArgs, metadataOnly, lock, passLock]] * len(fileFrame)), fileFrame.iterrows()))
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
        thread = th.Thread(target=_loadIms, args=[qout, qin, metadataOnly, lock])
        thread.start()
        cubes = []
        if processorFunc:
            wrappedFunc = _procWrap(processorFunc, passLock, lock)
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
