# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 11:31:48 2018

@author: backman05
"""
from pwspython import ImCube, reflectanceHelper
from glob import glob
import matplotlib.pyplot as plt
import numpy as np
import psutil
import multiprocessing as mp
import threading as th
import typing
import os
from time import time
import pandas as pd


def _loadIms(q, fileDict, specifierNames):
        def a(arg, specifiers:typing.List[str] = []):
            if isinstance(arg,dict):
                for k,v in arg.items():
                    a(v,specifiers + [k])
            elif isinstance(arg,list):
                for file in arg:
                    fileSpecifiers = specifiers
                    _ =ImCube.loadAny(file)
                    if specifierNames is None:
                        _.specifiers = fileSpecifiers
                    else:
                        for i,name in enumerate(specifierNames):
                            setattr(_,name,fileSpecifiers[i])
                    _.filename = os.path.split(file)[1]
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

def _countIms(fileDict):
    def a(arg, numIms):
        if isinstance(arg,dict):
            for k,v in arg.items():
                numIms = a(v,numIms)
        elif isinstance(arg,list):
            numIms += len(arg)
            
        else:
            raise TypeError(f'Filedict must only contain Dict and List, not an item of type: {type(arg)}')
        return numIms
    return a(fileDict, 0)


def loadAndProcess(fileDict:dict, processorFunc = None, specifierNames:list = None, parallel = False, procArgs = []):
    sTime = time()
    numIms = _countIms(fileDict)
    m = mp.Manager()
    q = m.Queue()
    thread = th.Thread(target = _loadIms, args=[q, fileDict, specifierNames])
    thread.start()

    if processorFunc is not None:
        #%% Start processing
        if parallel:
            po = mp.Pool(processes = psutil.cpu_count(logical=False)-1)
            cubes = po.starmap(processorFunc, [[q,*procArgs]]*numIms)
        else:
            cubes = [processorFunc(q,*procArgs) for i in range(numIms)]
    else:
        cubes = [q.get() for i in range(numIms)]
    thread.join()
    print(f"Loading took {time()-sTime} seconds")
    return cubes

def plotExtraReflection(types:list, settings:list, rootDir:str, processorFunc:callable, save = False):
    fileDict = {t:{s:glob(os.path.join(rootDir,t,s,'Cell*')) for s in settings} for t in types}
    cubes = loadAndProcess(fileDict, processorFunc, specifierNames = ['type', 'setting'], parallel = True)


    mask = [i for i in cubes if i.setting == settings[-1]][0].selectROI()
    
    #%% load theory reflectance
    AirR = reflectanceHelper.getReflectance('air','glass', index = cubes[0].wavelengths)
    WaterR = reflectanceHelper.getReflectance('water','glass',index = cubes[0].wavelengths)
    #%% Select cubes
    subs = [i for i in cubes if i.type == types[-1]]
    cubes = [i for i in cubes if i.type != types[-1]]
    
    
    #%% plot
    factors = {}
    reflections = {}
    fig, ax = plt.subplots() #For extra reflections
    plt.title("Extra Reflection")
    ax.set_ylabel("%")
    ax.set_xlabel("nm")
    fig2, ax2 = plt.subplots() # for correction factor
    plt.title("Uncorrected A/W reflection ratio")

    for sett in settings:
        scubes = [i for i in cubes if (i.setting == sett)] #select out some images
        airCubes = [i for i in scubes if i.type == types[0]]
        waterCubes = [i for i in scubes if i.type == types[1]]
    
        allCombos = []
        for air in airCubes:
            for wat in waterCubes:
                    allCombos.append((air,wat))
        
        Rextras = []
        for air,water in allCombos:
            Rextras.append(((AirR * water.getMeanSpectra(mask)[0]) - (WaterR * air.getMeanSpectra(mask)[0])) / (air.getMeanSpectra(mask)[0] - water.getMeanSpectra(mask)[0]))
            ax.plot(air.wavelengths, Rextras[-1], label = '{} Air:{}ms Water:{}ms'.format(sett, int(air.exposure), int(water.exposure)))

        for air,water in allCombos:
            plt.figure()
            plt.title("{}, Air:{}ms, Water:{}ms".format(sett, int(air.exposure), int(water.exposure)))
            refIm = (((AirR[np.newaxis,np.newaxis,:] * water.data) - (WaterR[np.newaxis,np.newaxis,:] * air.data)) / (air.data - water.data)).mean(axis=2)
            plt.imshow(refIm,vmin=np.percentile(refIm,.5),vmax=np.percentile(refIm,99.5))
            plt.colorbar()
            ax2.plot(air.getMeanSpectra(mask)[0]/water.getMeanSpectra(mask)[0], label="{}, Air:{}ms, Water:{}ms".format(sett, int(air.exposure), int(water.exposure)))
        
        print("{} correction factor".format(sett))
        Rextra = np.array(Rextras)
        factors[sett] = (Rextra.mean() + WaterR.mean()) / WaterR.mean()
        reflections[sett] = Rextra.mean(axis = 0)
        print(factors[sett])
    ax.legend()
    ax2.legend()
    
    df = pd.DataFrame(factors, index = [0])
    df2 = pd.DataFrame(reflections,index = cubes[0].wavelengths)
    if save:
        df.to_csv(os.path.join(rootDir, 'calcReflections','factors.csv'))
        df2.to_csv(os.path.join(rootDir, 'calcReflections','reflections.csv'))