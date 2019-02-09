# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 11:41:32 2018

@author: Nick
"""
#from __future__ import annotations

import numpy as np
import tifffile as tf
import os
import json
import matplotlib.pyplot as plt
from matplotlib import widgets
from matplotlib import path
from glob import glob
import typing
import numbers
import scipy.signal as sps
import scipy.io as spio
from otherClasses import CameraCorrection, ICMetaData

class ImCube:
    Metadata = ICMetaData
    CameraCorrection = CameraCorrection
    ''' A class representing a single acquisition of PWS. Contains methods for loading and saving to multiple formats as well as common operations used in analysis.'''
    def __init__(self,data, metadata:ICMetaData, dtype = np.float32, filePath = None):
        assert isinstance(data,np.ndarray)
        assert isinstance(metadata,dict)
        self.filePath = filePath
        self._hasBeenNormalized = False #Keeps track of whether or not we have normalized by exposure so that we don't do it twice.
        self._cameraCorrected = False
        self.data = data.astype(dtype)
        self.metadata = metadata
        self.wavelengths = tuple(self.metadata['wavelengths'])
        if self.data.shape[2] != len(self.wavelengths):
            raise ValueError("The length of the wavelengths list doesn't match the wavelength axis of the data array")
        
    @classmethod
    def loadAny(cls, directory):
        try:
            return ImCube.fromTiff(directory)
        except Exception as e:
            try:
                files = glob(os.path.join(directory,'*.comp.tif'))
                return ImCube.decompress(files[0])
            except:
                try:
                    return ImCube.fromOldPWS(directory)
                except:
                    raise Exception(f"Could not find a valid PWS image cube file at {directory}.")
    @classmethod
    def fromOldPWS(cls,directory):
        md = ICMetadata.fromOldPWS(directory)
        with open(os.path.join(directory,'image_cube'),'rb') as f:
            data = np.frombuffer(f.read(),dtype=np.uint16)
        data = data.reshape((md['imgHeight'],md['imgWidth'],len(md['wavelengths'])),order='F')
        return cls(data, md, filePath = directory)

    @classmethod
    def fromTiff(cls,directory):
        metadata = ICMetadata.fromTiff(directory)
        if os.path.exists(os.path.join(directory,'MMStack.ome.tif')):
            path = os.path.join(directory,'MMStack.ome.tif')
        elif os.path.exists(os.path.join(directory,'pws.tif')):
            path = os.path.join(directory,'pws.tif')
        else:
            raise OSError("No Tiff file was found at:", directory)    
        with tf.TiffFile(path) as tif:
            data = np.rollaxis(tif.asarray(),0,3) #Swap axes to match y,x,lambda convention.
        return cls(data,metadata, filePath = directory)
        
    def toOldPWS(self,directory):
        if os.path.exists(directory):
            raise OSError("The specified directory already exists.")
        os.mkdir(directory)
        m = self.metadata
        info2 = {'info2':np.array([m['wavelengths'][0],0,m['wavelengths'][-1],m['exposure'],0,0,0,0,0,0], dtype=object)}

        try:
            info3 = {'info3':np.array([m['systemId'],m['exposure'],m['imgHeight'],m['imgWidth'],0,0,0,0,0,0,0,0], dtype=object)} #the old way
        except:
            info3 = {'info3':np.array([m['system'],m['exposure'],self.data.shape[0],self.data.shape[1],0,0,0,0,0,0,0,0], dtype=object)}    #The new way
        wv = {"WV":[float(i) for i in m['wavelengths']]}
        savemat(os.path.join(directory,'info2'),info2)
        savemat(os.path.join(directory,'info3'),info3)
        savemat(os.path.join(directory,'WV'),wv)
        imbd = self.data[:,:,self.data.shape[-1]//2]
        savemat(os.path.join(directory,'image_bd'),{'image_bd':imbd})
        nimbd = imbd-np.percentile(imbd,0.01) #.01 percent saturation
        nimbd = nimbd/np.percentile(nimbd,99.99)
        nimbd = (nimbd*255).astype(np.uint8)
        im = tf.TiffWriter(os.path.join(directory,'image_bd.tif'))
        im.save(nimbd)
        im.close()
        with open(os.path.join(directory,'image_cube'),'wb') as f:
            f.write(self.data.astype(np.uint16).tobytes(order='F'))
            
    def compress(self,outpath):
        im = self.data #3d array of pixel data
        im = im.astype(np.int32)   #convert to signed integer to avoid overflow during processing.
        mins = []   #A list to store the minimum value offsets of each of secondary frames.
        for i in range(im.shape[-1]-1,0,-1): #The first image is unchanged. the rest are expressed as the difference between themselves and the frame before them.
            im[:,:,i] = im[:,:,i] - im[:,:,i-1]   #Subtract the image from the frame before it.
            mins.append(im[:,:,i].min())    #record the new minimum value
            im[:,:,i] -= mins[-1]   #Subtract by the minimum. this ensures that the minimum is 0. If it was negative we would have an issue saving as uint8
        mins = mins[::-1]   #reverse the list to go back to forward order
        metadata = self.metadata
        metadata["compressionMins"] = [int(i) for i in mins] #This is needed for json compatability
        with open(outpath,'wb') as f:
            w=tf.TiffWriter(f)
            w.save(np.rollaxis(im.astype(np.uint16),-1,0),metadata = metadata, compress = 1)
            w.close()
    
    @classmethod
    def decompress(cls,inpath):
        with open(inpath,'rb') as f:
            t = tf.TiffFile(f)
            im = np.rollaxis(t.asarray(),0,3)
            md = ICMetadata(json.loads(t.pages[0].tags['ImageDescription'].value))
        mins = md["compressionMins"]
        del md["compressionMins"]
        for i in range(1,im.shape[-1]):
            im[:,:,i] = im[:,:,i] + mins[i-1] + im[:,:,i-1]
        return cls(im,md)
    
    def toTiff(self, outpath, dtype = np.uint16):
        im = self.data
        im = im.astype(dtype)
        os.mkdir(outpath)
        with tf.TiffWriter(open(os.path.join(outpath, 'pws.tif'),'wb')) as w:
            w.save(np.rollaxis(im, -1, 0), metadata=self.metadata)
    
    def plotMean(self):
        fig,ax = plt.subplots()
        mean = np.mean(self.data,axis=2)
        im = ax.imshow(mean)
        plt.colorbar(im, ax = ax)
        return fig,ax
    
    def normalizeByExposure(self):
        if not self._hasBeenNormalized:
            self.data = self.data / self.metadata['exposure']
        else:
            raise Exception("The ImCube has already been normalized by exposure.")
        self._hasBeenNormalized = True
    
    def correctCameraEffects(self, correction:'CameraCorrection', binning:int = None):
        #Subtracts the darkcounts from the data. count is darkcounts per pixel. binning should be specified if it wasn't saved in the micromanager metadata.
        if self._cameraCorrected:
            print("This ImCube has already had it's camera correction applied!")
            return
        if binning is None:
            try:
                binning = self.metadata['MicroManagerMetadata']['Binning']
                if isinstance(binning, dict): #This is due to a property map change from beta to gamma
                    binning = binning['scalar']
            except:
                print('Micromanager binning data not found. Assuming no binning.')
                binning = 1
        count = correction.darkCounts * binning**2    #Account for the fact that binning multiplies the darkcount.
        self.data = self.data - count
        
        if correction.linearityPolynomial is None:
            pass
        else:
            self.data = np.polynomial.polynomial.polyval(self.data, [0]+correction.linearityPolynomial) #The [0] is the y-intercept (already handled by the darkcount)
        
        self._cameraCorrected = True
        return
        
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
    
    def _wavelengthsMatch(self, other:'ImCube') -> bool:
        return self.wavelengths == other.wavelengths
    
    def __add__(self, other:typing.Union['ImCube',numbers.Real,np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._wavelengthsMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data + other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other, (numbers.Real, np.ndarray)):
            return ImCube(self.data + other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Addition is not supported between ImCube and {type(other)}")

    def __sub__(self, other:typing.Union['ImCube',numbers.Real,np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._wavelengthsMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data - other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other, (numbers.Real, np.ndarray)):
            return ImCube(self.data - other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Subtraction is not supported between ImCube and {type(other)}")
    
    def __mul__(self, other:typing.Union['ImCube',numbers.Real, np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._wavelengthsMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data * other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other,(numbers.Real, np.ndarray)):
            return ImCube(self.data * other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Multiplication is not supported between ImCube and {type(other)}")
    __rmul__ = __mul__ #multiplication is commutative. let it work both ways.
    
    def __truediv__(self, other:typing.Union['ImCube',numbers.Real, np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._wavelengthsMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data / other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other, (numbers.Real, np.ndarray)):
            return ImCube(self.data / other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Division is not supported between ImCube and {type(other)}")


    def wvIndex(self, start, stop):
        wv = np.array(self.wavelengths)
        iStart = np.argmin(np.abs(wv - start))
        iStop = np.argmin(np.abs(wv - stop))
        iStop += 1 #include the end point
        if iStop >= len(wv): #Include everything
            iStop = None
        md = self.metadata
        md['wavelengths'] = wv[iStart:iStop]
        return ImCube(self[:,:,iStart:iStop], md, filePath = self.filePath)
    
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
        
    def normalizeByReference(self, reference:'ImCube'):
        self.data = self.data / reference.data
        self.metadata['normalizationReference'] = reference.filePath