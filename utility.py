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
import itertools

'''Local Functions'''
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

def _interpolateNans(arr):
    def interp1(arr1):
        nans = np.isnan(arr1)
        f = lambda z: z.nonzero()[0]
        arr1[nans] = np.interp(f(nans), f(~nans), arr1[~nans])
        return arr1
    arr = np.apply_along_axis(interp1, 2, arr)
    return arr

'''User Functions'''
def loadAndProcess(fileDict:dict, processorFunc = None, specifierNames:list = None, parallel = False, procArgs = []) -> typing.List[ImCube]:
    sTime = time()
    numIms = _countIms(fileDict)
    m = mp.Manager()
    q = m.Queue()
    thread = th.Thread(target = _loadIms, args=[q, fileDict, specifierNames])
    thread.start()

    if processorFunc is not None:
        # Start processing
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

def plotExtraReflection(cubes:list, selectMaskUsingSetting:str = None) -> (pd.DataFrame, pd.DataFrame):
    '''Expects a list of ImCubes which each has a `material` property matching one of the materials in the `ReflectanceHelper` module and a
    `setting` property labeling how the microscope was set up for this image.
    '''
    
    #Error checking
    assert isinstance(cubes[0], ImCube)
    assert hasattr(cubes[0],'material')
    assert hasattr(cubes[0],'setting')
    ##
    if selectMaskUsingSetting is None:        
        mask = cubes
    else:
        mask = [i for i in cubes if (i.setting == selectMaskUsingSetting)]
    mask = mask[0].selectROI()
    
    # load theory reflectance
    theoryR = {}
    materials = set([i.material for i in cubes])
    for material in materials: #For each unique material in the `cubes` list
        theoryR[material] = reflectanceHelper.getReflectance(material,'glass', index=cubes[0].wavelengths)
  
    # plot
    factors = {}
    reflections = {}
    fig, ax = plt.subplots() #For extra reflections
    plt.title("Extra Reflection")
    ax.set_ylabel("%")
    ax.set_xlabel("nm")
    matCombos = list(itertools.combinations(materials, 2))
    fig2, ratioAxes = plt.subplots(nrows = len(matCombos)) # for correction factor
    if not isinstance(ratioAxes, np.ndarray): ratioAxes = np.array(ratioAxes) #If there is only one axis we still want it to be a list for the rest of th code
    ratioAxes = dict(zip(matCombos,ratioAxes))
    for combo in matCombos:
        ratioAxes[combo].set_title(f'{combo[0]}/{combo[1]} reflection ratio')
        ratioAxes[combo].plot(theoryR[combo[0]]/theoryR[combo[1]], label='Theory')

    settings = set([i.setting for i in cubes]) #Unique setting values
    for sett in settings:
        for matCombo in matCombos:
            scubes = [i for i in cubes if (i.setting == sett)] #select out some images
            matCubes = {material:[cube for cube  in scubes if cube.material==material] for material in matCombo}
        
            allCombos = []
            for combo in itertools.product(*matCubes.values()):
                allCombos.append(dict(zip(matCubes.keys(), combo)))
            
            Rextras = []
            for combo in allCombos:
                mat1,mat2 = combo.keys()
                Rextras.append(((theoryR[mat1] * combo[mat2].getMeanSpectra(mask)[0]) - (theoryR[mat2] * combo[mat1].getMeanSpectra(mask)[0])) / (combo[mat1].getMeanSpectra(mask)[0] - combo[mat2].getMeanSpectra(mask)[0]))
                ax.plot(combo[mat1].wavelengths, Rextras[-1], label = f'{sett} {mat1}:{int(combo[mat1].exposure)}ms {mat2}:{int(combo[mat2].exposure)}ms')
    
                plt.figure()
                plt.title(f"Reflectance %. {sett}, {mat1}:{int(combo[mat2].exposure)}ms, {mat2}:{int(combo[mat2].exposure)}ms")
                _ = ((theoryR[mat1][np.newaxis,np.newaxis,:] * combo[mat2].data) - (theoryR[mat2][np.newaxis,np.newaxis,:] * combo[mat1].data)) / (combo[mat1].data - combo[mat2].data)
                _[np.isinf(_)] = np.nan
                if np.any(np.isnan(_)):
                    _ = _interpolateNans(_) #any division error resulting in an inf will really mess up our refIm. so we interpolate them out.
                refIm = _.mean(axis=2)
                plt.imshow(refIm,vmin=np.percentile(refIm,.5),vmax=np.percentile(refIm,99.5))
                plt.colorbar()
                ratioAxes[matCombo].plot(combo['air'].getMeanSpectra(mask)[0]/combo['water'].getMeanSpectra(mask)[0], label="{}, Air:{}ms, Water:{}ms".format(sett, int(combo['air'].exposure), int(combo['water'].exposure)))
        
        print("{} correction factor".format(sett))
        Rextra = np.array(Rextras)
        factors[sett] = (Rextra.mean() + theoryR['water'].mean()) / theoryR['water'].mean()
        reflections[sett] = Rextra.mean(axis = 0)
        print(factors[sett])
    ax.legend()
    ax2.legend()
    
    df = pd.DataFrame(factors, index = [0])
    df2 = pd.DataFrame(reflections,index = cubes[0].wavelengths)
    return df, df2