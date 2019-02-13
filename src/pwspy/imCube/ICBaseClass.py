# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 16:47:22 2019

@author: Nick
"""
import numpy as np
from .otherClasses import ICMetaData
import scipy.signal as sps
import scipy.io as spio
import matplotlib.pyplot as plt
from matplotlib import widgets
from matplotlib import path
import os
from glob import glob


class ICBase:
    def __init__(self,data, metadata:ICMetaData, index:tuple, dtype = np.float32, filePath = None):
        assert isinstance(data,np.ndarray)
        assert isinstance(metadata,dict)
        self.filePath = filePath
        self.data = data.astype(dtype)
        self.metadata = metadata
        self._index = index
        if self.data.shape[2] != len(self._index):
            raise ValueError("The length of the index list doesn't match the index axis of the data array")
    
    @property
    def index(self):
        return self._index
            
    def plotMean(self):
        fig,ax = plt.subplots()
        mean = np.mean(self.data,axis=2)
        im = ax.imshow(mean)
        plt.colorbar(im, ax = ax)
        return fig,ax
    
    def getMeanSpectra(self,mask = None):
        if mask is None:
            mask = np.ones(self.data.shape[:-1], dtype=np.bool)
        mean = self.data[mask].mean(axis=0)
        std = self.data[mask].std(axis=0)
        return mean,std
    
    def selectLassoROI(self):
        mask = np.zeros((self.data.shape[0],self.data.shape[1]),dtype=np.bool)

        fig,ax = self.plotMean()
        fig.suptitle("Close to accept ROI")
        x,y = np.meshgrid(np.arange(self.data.shape[0]),np.arange(self.data.shape[1]))
        coords = np.vstack((y.flatten(),x.flatten())).T
        
        def onSelect(verts):
            p = path.Path(verts)
            ind = p.contains_points(coords,radius=0)
            mask[coords[ind,1],coords[ind,0]] = True
            
        l = widgets.LassoSelector(ax,onSelect)

        while plt.fignum_exists(fig.number):
            fig.canvas.flush_events()
        return mask
    
    def selectRectangleROI(self,xSlice = None,ySlice = None):
        #X and Y slice allow manual selection of the range.
        mask = np.zeros((self.data.shape[0],self.data.shape[1]),dtype=np.bool)
        slices= {'y':ySlice, 'x':xSlice}
        if (slices['x'] is not None) and (slices['y'] is not None):
            if not hasattr(slices['x'],'__iter__'):
                slices['x'] = (slices['x'],)
            if not hasattr(slices['y'],'__iter__'):
                slices['y'] = (slices['y'],) 
            slices['x'] = slice(*slices['x'])
            slices['y'] = slice(*slices['y'])
            mask[slices['y'],slices['x']] = True       
        else:
            fig,ax = self.plotMean()
            fig.suptitle("Close to accept ROI")

            def rectSelect(mins,maxes):
                y = [int(mins.ydata),int(maxes.ydata)]
                x = [int(mins.xdata),int(maxes.xdata)]
                slices['y'] = slice(min(y),max(y))
                slices['x'] = slice(min(x),max(x))
                mask[slices['y'],slices['x']] = True
                
            r = widgets.RectangleSelector(ax,rectSelect)

            while plt.fignum_exists(fig.number):
                fig.canvas.flush_events()
        return mask, (slices['y'], slices['x']) 
             
    def __getitem__(self,slic):
        return self.data[slic]
    
    def filterDust(self, kernelRadius:int):
        def _gaussKernel(radius:int):
            #A kernel that goes to 1 std. It would be better to go out to 2 or 3 std but then you need a larger kernel which greatly increases convolution time.
            lenSide = 1+2*radius
            side = np.linspace(-1,1,num=lenSide)
            X,Y = np.meshgrid(side, side)
            R = np.sqrt(X**2 + Y**2)
            k = np.exp(-(R**2)/2)
            k = k/k.sum() #normalize so the total is 1.
            return k
        
        kernel = _gaussKernel(kernelRadius)
        for i in range(self.data.shape[2]):
            m = self.data[:,:,i].mean() #By subtracting the mean and then adding it after convolution we are effectively padding the convolution with the mean.
            self.data[:,:,i] = sps.convolve(self.data[:,:,i]-m,kernel,mode='same')+m
            
    def saveMask(self,mask:np.ndarray,number:int, suffix:str):
        assert not self.filePath is None
        assert len(mask.shape)==2
        assert mask.shape == self.data.shape[:2]
        spio.savemat(os.path.join(self.filePath,f'BW{number}_{suffix}.mat'),{"BW":mask.astype(np.bool)})
        
    def loadMask(self,number:int, suffix:str):
        assert not self.filePath is None
        mask = spio.loadmat(os.path.join(self.filePath,f'BW{number}_{suffix}.mat'))['BW'].astype(np.bool)
        assert len(mask.shape)==2
        assert mask.shape == self.data.shape[:2]
        return mask
    
    def getMasks(self):
        assert not self.filePath is None
        files = glob(os.path.join(self.filePath,'BW*.mat'))
        masks = {}
        for f in files:
            num, suffix = os.path.split(f)[-1][2:-4].split('_')
            if suffix in masks:
                masks[suffix].append(num)
            else:
                masks[suffix] = [num]
        for k,v in masks.items():
            v.sort()
        return masks
    
    def deleteMask(self, number:int, suffix:str):
        assert not self.filePath is None
        os.remove(os.path.join(self.filePath, f'BW{number}_{suffix}.mat'))
    
    def _indicesMatch(self, other:'ICBase') -> bool:
        return self._index == other._index