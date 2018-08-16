# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 11:41:32 2018

@author: Nick
"""
import numpy as np
from scipy.io import loadmat,savemat
import tifffile as tf
import os
import json

class ImCube:
    def __init__(self,data,metadata):
        assert isinstance(data,np.ndarray)
        assert isinstance(metadata,dict)
        self._data = data
        self.metadata = metadata
        
    @classmethod
    def fromOldPWS(cls,directory):
        try:
            md = json.load(open(os.path.join(directory,'pwsmetadata.txt')))
        except: #have to use the old metadata
            print("Json metadata not found")
            info2 = list(loadmat(os.path.join(directory,'info2.mat'))['info2'].squeeze())
            info3 = list(loadmat(os.path.join(directory,'info3.mat'))['info3'].squeeze())
            wv = list(loadmat(os.path.join(directory,'wv.mat'))['WV'].squeeze())
            md = {'startWv':info2[0],'stepWv':info2[1],'stopWv':info2[2],
                 'exposure':info2[3],'time':'Unkn','systemId':info3[0],
                 'imgHeight':int(info3[2]),'imgWidth':int(info3[3]),'waveLengths':wv}
        with open(os.path.join(directory,'image_cube'),'rb') as f:
            data = np.frombuffer(f.read(),dtype=np.uint16)
        data = data.reshape((md['imgHeight'],md['imgWidth'],len(md['waveLengths'])),order='F')
        return cls(data, md)

    @classmethod
    def fromTiff(cls,directory):
        with tf.TiffFile(os.path.join(directory,'MMStack.ome.tif')) as tif:
            data = np.rollaxis(tif.asarray(),0,3) #Swap axes to match y,x,lambda convention.
        metadata = json.load(open(os.path.join(directory,'pwsmetadata.txt'),'r'))
        return cls(data,metadata)
        
    def toOldPWS(self,directory):
        if os.path.exists(directory):
            raise OSError("The specified directory already exists.")
        os.mkdir(directory)
        m = self.metadata
        info2 = {'info2':[m['waveLengths'][0],0,m['waveLengths'][-1],m['exposure'],0,0,0,0,0,0]}
        info3 = {'info3':[m['systemId'],m['exposure'],m['imgHeight'],m['imgWidth'],0,0,0,0,0,0,0,0]}
        wv = {"WV":[float(i) for i in m['waveLengths']]}
        savemat(os.path.join(directory,'info2'),info2)
        savemat(os.path.join(directory,'info3'),info3)
        savemat(os.path.join(directory,'WV'),wv)
        imbd = self._data.mean(axis=-1)
        savemat(os.path.join(directory,'image_bd'),{'image_bd':imbd})
        nimbd = imbd-np.percentile(imbd,0.1) #.5 percent saturation
        nimbd = nimbd/np.percentile(nimbd,99.9)
        nimbd = (nimbd*255).astype(np.uint8)
        im = tf.TiffWriter(os.path.join(directory,'image_bd.tif'))
        im.save(nimbd)
        im.close()
        with open(os.path.join(directory,'image_cube'),'wb') as f:
            f.write(self._data.tobytes(order='F'))
            
    def compress(self,outpath):
        im = self._data #3d array of pixel data
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
            md = json.loads(t.pages[0].tags['ImageDescription'].value)
        mins = md["compressionMins"]
        del md["compressionMins"]
        for i in range(1,im.shape[-1]):
            im[:,:,i] = im[:,:,i] + mins[i-1] + im[:,:,i-1]
        return cls(im,md)
    
    def __getitem__(self,slic):
        return self._data[slic]
