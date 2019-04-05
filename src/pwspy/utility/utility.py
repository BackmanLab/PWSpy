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
import pandas as pd
import psutil
from pwspy import ImCube
from pwspy.imCube.ICMetaDataClass import ICMetaData

'''Local Functions'''
def _loadIms(qout, qin, lock):
    """When not running in parallel this function is executed in a separate thread to load ImCubes and populate a Queue
    with them."""
    while not qin.empty():
        index, row = qin.get()
        print('starting', row['cubes'])
        im = ImCube.loadAny(row['cubes'], lock=lock)
        row['cubes'] = im
        qout.put(row)
        perc = psutil.virtual_memory().percent
        print("Memory Usage: ", perc, '%')
        if perc >= 95:
            print('quitting')
            return

def _procWrap(procFunc):
    def func(row, procFuncArgs):
        im = row['cubes']
        ret = procFunc(im, *procFuncArgs)
        row['cubes'] = ret
        return row
    return func

def _loadThenProcess(procFunc, procFuncArgs, lock, row):
    """Handles loading the ImCubes from file and if needed then calling the processorFunc. This function will be executed
     on each core when running in parallel. If not running in parallel then _loadIms will be used."""
    index, row = row
    if isinstance(row['cubes'], str):
        im = ImCube.loadAny(row['cubes'], lock=lock)
    elif isinstance(row['cubes'], ICMetaData):
        im = ImCube.fromMetadata(row['cubes'], lock=lock)
    else:
        raise TypeError("files specified to the loader must be either str or ICMetaData")
    print("Run", row['cubes'])
    ret = procFunc(im, *procFuncArgs)
    row['cubes'] = ret
    return row


'''User Functions'''


def loadAndProcess(fileFrame: pd.DataFrame, processorFunc: Optional = None,
                   parallel: Optional=False, procArgs: Optional = None) -> pd.DataFrame:
    """    A convenient function to load a series of ImCubes from a list or dictionary of file paths.

    Parameters
    ----------
    fileFrame
        A dataframe containing a column of ImCube file paths titled 'cubes' and other columns to act as specifiers for each cube.
        If no specifiers are used this can just be a list of file paths.
    processorFunc
        A function that each loaded cell should be passed to. The first argument of processorFunc should be the loaded
        ImCube. Additional arguments can be passed to processorFunc using the procArgs variable.
    parallel
        default is False. If True then the loading and processing will be performed in parallel on multiple cores,
        otherwise it will be done using multithreading on a single core. Setting this to true can result if big speedups
        if the time to run processorFunc is greater than the time to load an ImCube from file.
    procArgs
        Optional arguments to pass to processorFunc

    Returns
    -------
    Dataframe or list
        returns an object of the same form as fileFrame except the ImCube file paths have been replaced by ImCube Object.
        If using processorFunc the return values from processorFunc will be returned rather than ImCube Objects.
    """
    if procArgs is None:
        procArgs = []
    # Error checking
    if 'cubes' not in fileFrame.columns:
        raise IndexError("The fileFrame must contain a 'cubes' column.")
    numThreads = 2  # even this might be unnecesary. don't bother going higher.
    print(f"Starting loading {len(fileFrame)} files.")
    sTime = time()
    if parallel:
        if processorFunc is None:
            raise Exception("Running in parallel with no processorFunc is a bad idea.")
        m = mp.Manager()
        lock = m.Lock()
        po = mp.Pool(processes=psutil.cpu_count(logical=False) - 1)
        try:
            cubes = po.starmap(_loadThenProcess, zip(*zip(*[[processorFunc, procArgs, lock]] * len(fileFrame)), fileFrame.iterrows()))
        finally:
            po.close()
    else:
        qout = queue.Queue()
        qin = queue.Queue()
        [qin.put(f) for f in fileFrame.iterrows()]
        lock = th.Lock()
        threads = [th.Thread(target=_loadIms, args=[qout, qin, lock]) for i in range(numThreads)]
        [thread.start() for thread in threads]
        print('threads started')
        if processorFunc is not None:
            cubes = [_procWrap(processorFunc)(qout.get(), *procArgs) for i in range(len(fileFrame))]
        else:
            cubes = [qout.get() for i in range(len(fileFrame))]
        [thread.join() for thread in threads]
    print(f"Loading took {time() - sTime} seconds")
    return pd.DataFrame(cubes)
