# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 11:31:48 2018

@author: backman05
"""
from pwspython import ImCube
import psutil
import multiprocessing as mp
import threading as th

def loadAndProcessParallel(fileDict:dict, processorFunc = None):
    def loadIms(fileDict):
        for t, v in fileDict.items():
            for s, files in v.items():    
                for file in files:
                    _ =ImCube.loadAny(file)
                    _.type = t
                    _.setting = s
                    _.exposure = _.metadata['exposure']
                    q.put(_)
                    perc = psutil.virtual_memory().percent
                    print(file)
                    print("Memory Usage: ", perc,'%')
                    if perc >= 95:
                        del cubes
                        print('quitting')
                        quit()  
    numIms = 0
    for i, v in fileDict.items():
        for j, lis in v.items():
            numIms += len(lis)
    m = mp.Manager()
    q = m.Queue()
    thread = th.Thread(target = loadIms, args=[fileDict])
    thread.start()

    if processorFunc is not None:
        #%% Start processing in parallel
        po = mp.Pool(processes = psutil.cpu_count(logical=False)-1)
        cubes = po.map(processorFunc, [q]*numIms)
        thread.join()
    else:
        cubes = [q.get() for i in range(numIms)]
    return cubes