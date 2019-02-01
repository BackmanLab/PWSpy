# -*- coding: utf-8 -*-
"""
Created on Thu Oct 11 11:31:48 2018

@author: backman05
"""
from pwspython import ImCube
import matplotlib.pyplot as plt
import numpy as np
import psutil
import multiprocessing as mp
import threading as th
import typing
import os
from time import time
from threading import Timer
import matplotlib.gridspec as gridspec


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
    #Error checking
    if not specifierNames is None:
        recursionDepth = 0
        fileStructure = fileDict
        while not isinstance(fileStructure, list):
            fileStructure = fileStructure[list(fileStructure.keys())[0]]
            recursionDepth += 1
        if recursionDepth != len(specifierNames):
            raise ValueError("The length of specifier names does not match the number of layers of folders in the fileDict")
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


def plot3d(X):
    class perpetualTimer():
       def __init__(self,t,parent):
          self.t=t
          self.hFunction = parent.increment
          self.thread = Timer(self.t,self.handle_function)
          self.running = False
       def handle_function(self):
          self.hFunction()
          self.thread = Timer(self.t,self.handle_function)
          if self.running:
              self.thread.start()
       def start(self):
          self.thread.start()
          print('start')
          self.running=True
       def cancel(self):
          print('cancel')
#          self.thread.cancel()
          self.running=False


    class IndexTracker(object):
        def __init__(self, ax, X):
            self.ax = ax
#            ax[0].set_title('use scroll wheel to navigate images')
            self.X = X
            self.max = np.percentile(self.X,99.9)
            self.min = np.percentile(self.X,0.1)
            rows, cols, self.slices = X.shape
            self.coords = (100,100, self.slices//2)
            self.ax[0].get_xaxis().set_visible(False)
            self.ax[0].get_yaxis().set_visible(False)
            lw=0.5
            self.vline = ax[0].plot([100,100],[0,X.shape[0]],'r',linewidth = lw)[0]
            self.hline = ax[0].plot([0,X.shape[1]],[100,100],'r',linewidth = lw)[0]
            self.line2 = ax[1].plot([0,X.shape[1]],[100,100],'r',linewidth = lw)[0]
            self.line3 = ax[2].plot([100,100],[0,X.shape[0]],'r',linewidth = lw)[0]
            self.line4 = ax[3].plot([self.min,self.max],[100,100],'r',linewidth = lw)[0]
            self.yplot = ax[1].plot(self.X[:,self.coords[1],self.coords[2]], np.arange(self.X.shape[0]))[0]
            self.xplot = ax[2].plot(np.arange(self.X.shape[1]),self.X[self.coords[0],:,self.coords[2]])[0]
            self.zplot = ax[3].plot(self.X[self.coords[0],self.coords[1],:], np.arange(self.X.shape[2]))[0]
            self.im = ax[0].imshow(self.X[:, :, self.coords[2]])
            self.im.set_clim(self.min,self.max)
            self.cbar = plt.colorbar(self.im, cax=ax[4], orientation='horizontal')
            ax[4].xaxis.set_ticks_position("top")
            self.auto=perpetualTimer(0.2,self)
            self.update()  
        def onscroll(self, event):
            if ((event.button == 'up') or (event.button=='down')):
                self.coords = (self.coords[0], self.coords[1], (self.coords[2] + int(event.step)) % self.slices)
            self.update()    
        def onpress(self,event):
            if event.key == 'a':
                if self.auto.running: self.auto.cancel() 
                else: self.auto.start()
        def onclick(self,event):
            if event.inaxes==self.ax[0]:
                self.coords = (int(event.xdata), int(event.ydata), self.coords[2])
            elif event.inaxes==self.ax[1]:
                self.coords = (self.coords[0], int(event.ydata), self.coords[2])
            elif event.inaxes==self.ax[2]:
                self.coords = (int(event.xdata), self.coords[1], self.coords[2])
            elif event.inaxes==self.ax[3]:
                self.coords = (self.coords[0], self.coords[1], int(event.ydata))
            
            self.update()
        def increment(self):
            self.coords = (self.coords[0], self.coords[1], self.coords[2]+1)
            if self.coords[2] >= self.X.shape[2]: self.coords =(self.coords[0], self.coords[1], self.coords[2]-self.X.shape[2])
            self.update()
        def update(self):
            self.im.set_data(self.X[:, :, self.coords[2]])
            self.yplot.set_data(self.X[:,self.coords[0],self.coords[2]],np.arange(self.X.shape[0]))
            self.ax[1].set_xlim(min(self.yplot.get_data()[0]), max(self.yplot.get_data()[0]))
            self.xplot.set_data(np.arange(self.X.shape[1]),self.X[self.coords[1],:,self.coords[2]])
            self.ax[2].set_ylim(min(self.xplot.get_data()[1]), max(self.xplot.get_data()[1]))
            self.zplot.set_data(self.X[self.coords[1],self.coords[0],:],np.arange(self.X.shape[2]))
            self.ax[3].set_xlim(self.min,self.max)
            self.hline.set_data(self.hline.get_data()[0],[self.coords[1],self.coords[1]] )
            self.vline.set_data([self.coords[0],self.coords[0]],  self.vline.get_data()[1])
            self.line3.set_data([self.coords[0],self.coords[0]], self.ax[2].get_ylim())
            self.line2.set_data( self.ax[1].get_xlim(),[self.coords[1],self.coords[1]])
            self.line4.set_data(self.line4.get_data()[0], [self.coords[2], self.coords[2]])
            self.im.axes.figure.canvas.draw()
            
    fig = plt.figure() 
    h,w,_ =X.shape 
    gs = gridspec.GridSpec(3, 3,hspace=0,width_ratios=[w*.2,w,w*.2], height_ratios=[h*.1,h,h*.2])
    ax = [plt.subplot(gs[1,1]),]
    ax.append(plt.subplot(gs[1,2], sharey=ax[0]))
    ax.append(plt.subplot(gs[2,1], sharex=ax[0]))
    ax.append(plt.subplot(gs[1,0]))
    ax.append(plt.subplot(gs[0,1]))
    ax[1].yaxis.set_ticks_position('right')

    gs.update(wspace=0)

#    gs.tight_layout(fig, h_pad=0, w_pad=0)
#    fig.subplots_adjust(wspace = 0)
#    fig.subplots_adjust(hspace = 0)


#bounds = [x.min(),x.max(),y.min(),y.max()]
#ax[0].imshow(data, cmap='gray', extent = bounds, origin='lower')
#ax[1].plot(data[:,w/2],Y[:,w/2],'.',data[:,w/2],Y[:,w/2])
#ax[1].axis([data[:,w/2].max(), data[:,w/2].min(), Y.min(), Y.max()])
#ax[2].plot(X[h/2,:],data[h/2,:],'.',X[h/2,:],data[h/2,:])

    tracker = IndexTracker(ax, X)
    
    fig.canvas.mpl_connect('key_press_event', tracker.onpress)
    fig.canvas.mpl_connect('scroll_event', tracker.onscroll)
    fig.canvas.mpl_connect('button_press_event', tracker.onclick)

    while plt.fignum_exists(fig.number):
        fig.canvas.flush_events()
    tracker.auto.cancel()
        
