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
from glob import glob
import typing
import numbers
from scipy.io import savemat
from .otherClasses import CameraCorrection
from .ICBaseClass import ICBase
from .ICMetaDataClass import ICMetaData

class ImCube(ICBase, ICMetaData):
    ''' A class representing a single acquisition of PWS. Contains methods for loading and saving to multiple formats as well as common operations used in analysis.'''
    
    def __init__(self,data, metadata:dict, dtype = np.float32, filePath = None):
        ICMetaData.__init__(self, metadata, filePath)
        ICBase.__init__(self, data, tuple(np.array(self.metadata['wavelengths']).astype(np.float32)), dtype=dtype)
        self._hasBeenNormalized = False #Keeps track of whether or not we have normalized by exposure so that we don't do it twice.
        self._cameraCorrected = False
    
    @property
    def wavelengths(self):
        return self.index
        
    @classmethod
    def loadAny(cls, directory):
        try:
            return ImCube.fromTiff(directory)
        except:
            try:
                files = glob(os.path.join(directory,'*.comp.tif'))
                return ImCube.decompress(files[0])
            except:
                try:
                    return ImCube.fromOldPWS(directory)
                except OSError:
                    raise OSError(f"Could not find a valid PWS image cube file at {directory}.")
    @classmethod
    def fromOldPWS(cls,directory):
        ret = ICMetaData.fromOldPWS(directory)
        with open(os.path.join(directory,'image_cube'),'rb') as f:
            data = np.frombuffer(f.read(),dtype=np.uint16)
        data = data.reshape((ret.metadata['imgHeight'],ret.metadata['imgWidth'],len(ret.metadata['wavelengths'])),order='F')
        return cls(data, ret.metadata, filePath = ret.filePath)

    @classmethod
    def fromTiff(cls,directory):
        ret = ICMetaData.fromTiff(directory)
        if os.path.exists(os.path.join(directory,'MMStack.ome.tif')):
            path = os.path.join(directory,'MMStack.ome.tif')
        elif os.path.exists(os.path.join(directory,'pws.tif')):
            path = os.path.join(directory,'pws.tif')
        else:
            raise OSError("No Tiff file was found at:", directory)    
        with tf.TiffFile(path) as tif:
            data = np.rollaxis(tif.asarray(),0,3) #Swap axes to match y,x,lambda convention.
        return cls(data,ret.metadata, filePath = directory)
        
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
        self._saveImBd(directory)
        with open(os.path.join(directory,'image_cube'),'wb') as f:
            f.write(self.data.astype(np.uint16).tobytes(order='F'))
            
    def _saveImBd(self, directory):
        imbd = self.data[:,:,self.data.shape[-1]//2]
        nimbd = imbd-np.percentile(imbd,0.01) #.01 percent saturation
        nimbd = nimbd/np.percentile(nimbd,99.99)
        nimbd = (nimbd*255).astype(np.uint8)
        im = tf.TiffWriter(os.path.join(directory,'image_bd.tif'))
        im.save(nimbd)
        im.close()
        
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
            md = ICMetaData(json.loads(t.pages[0].tags['ImageDescription'].value))
        mins = md["compressionMins"]
        del md["compressionMins"]
        for i in range(1,im.shape[-1]):
            im[:,:,i] = im[:,:,i] + mins[i-1] + im[:,:,i-1]
        return cls(im,md)
    
    def toTiff(self, outpath, dtype = np.uint16):
        im = self.data
        im = im.astype(dtype)
        os.mkdir(outpath)
        self._saveImBd(outpath)
        with tf.TiffWriter(open(os.path.join(outpath, 'pws.tif'),'wb')) as w:
            w.save(np.rollaxis(im, -1, 0), metadata=self.metadata)
    
    
    def normalizeByExposure(self):
        if not self._cameraCorrected:
            print("This ImCube has not yet been corrected for camera effects. are you sure you want to normalize by exposure?")
        if not self._hasBeenNormalized:
            self.data = self.data / self.metadata['exposure']
        else:
            raise Exception("The ImCube has already been normalized by exposure.")
        self._hasBeenNormalized = True
    
    def correctCameraEffects(self, correction:'CameraCorrection', binning:int = None):
        #Subtracts the darkcounts from the data. count is darkcounts per pixel. binning should be specified if it wasn't saved in the micromanager metadata.
        if self._cameraCorrected:
            raise Exception("This ImCube has already had it's camera correction applied!")
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
    
    
    def __add__(self, other:typing.Union['ImCube',numbers.Real,np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._indicesMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data + other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other, (numbers.Real, np.ndarray)):
            return ImCube(self.data + other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Addition is not supported between ImCube and {type(other)}")

    def __sub__(self, other:typing.Union['ImCube',numbers.Real,np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._indicesMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data - other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other, (numbers.Real, np.ndarray)):
            return ImCube(self.data - other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Subtraction is not supported between ImCube and {type(other)}")
    
    def __mul__(self, other:typing.Union['ImCube',numbers.Real, np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._indicesMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data * other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other,(numbers.Real, np.ndarray)):
            return ImCube(self.data * other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Multiplication is not supported between ImCube and {type(other)}")
    __rmul__ = __mul__ #multiplication is commutative. let it work both ways.
    
    def __truediv__(self, other:typing.Union['ImCube',numbers.Real, np.ndarray]) -> 'ImCube':
        if isinstance(other, ImCube):
            if not self._indicesMatch(other):
                raise ValueError("Imcube wavelengths are not compatible")
            return ImCube(self.data / other.data, self.metadata, filePath = self.filePath)
        elif isinstance(other, (numbers.Real, np.ndarray)):
            return ImCube(self.data / other, self.metadata, filePath = self.filePath)
        else:
            raise NotImplementedError(f"Division is not supported between ImCube and {type(other)}")
        
    def normalizeByReference(self, reference:'ImCube'):
        self.data = self.data / reference.data
        self.metadata['normalizationReference'] = reference.filePath
        
class FakeCube(ImCube):
    def __init__(self, num:int):
        x = y = np.arange(0,256)
        z = np.arange(0,100)
        Y,X,Z = np.meshgrid(y,x,z)
        freq = np.random.random()/4
        freq2 = np.random.random()/4
        data = np.exp(-np.sqrt((X-X.max()/2)**2+(Y-Y.max()/2)**2)/(x.max()/4))*(.75+0.25*np.cos(freq2*2*np.pi*Z))*(0.5+0.5*np.sin(freq*2*np.pi*X))
        md = {'wavelengths':z+500, 'exposure':100, 'time': '315'}
        super().__init__(data, md, filePath = f'Cell{num}')