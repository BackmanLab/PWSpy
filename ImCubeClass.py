# -*- coding: utf-8 -*-
"""
Created on Thu Aug  9 11:41:32 2018

@author: Nick
"""
import numpy as np
import tifffile
from scipy.io import loadmat,savemat
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
        tif = tifffile.TiffFile(os.path.join(directory,'MMStack.ome.tif'))
        metadata = json.load(open(os.path.join(directory,'pwsmetadata.txt'),'r'))
        data = np.rollaxis(tif.asarray(),0,3) #Swap axes to match y,x,lambda convention.
        return cls(data,metadata)
        
    def toOldPWS(self,directory):
        if os.path.exists(directory):
            raise OSError("The specified directory already exists.")
        os.mkdir(directory)
        m = self.metadata
        info2 = {'info2':[m['waveLengths'][0],0,m['waveLengths'][-1],m['exposure'],0,0,0,0,0,0]}
        info3 = {'info3':[m['systemId'],m['exposure'],m['imgHeight'],m['imgWidth'],0,0,0,0,0,0,0,0]}
        wv = {"WV":m['waveLengths']}
        savemat(os.path.join(directory,'info2'),info2)
        savemat(os.path.join(directory,'info3'),info3)
        savemat(os.path.join(directory,'WV'),wv)
        imbd = self._data.mean(axis=-1)
        savemat(os.path.join(directory,'image_bd'),{'image_bd':imbd})
        nimbd = imbd-imbd.min()
        nimbd = nimbd/nimbd.max()
        nimbd = (nimbd*255).astype(np.uint8)
        im = tifffile.TiffWriter(os.path.join(directory,'image_bd.tif'))
        im.save(nimbd)
        im.close()
        with open(os.path.join(directory,'image_cube'),'wb') as f:
            f.write(self._data.tobytes(order='F'))

    
    def __getitem__(self,slic):
        return self._data[slic]