# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 15:57:52 2019

@author: Nick
"""
import json
from scipy.io import loadmat
import os
import tifffile as tf
import typing


class ICMetaData(dict):
    def __init__(self, metadata):
        assert isinstance(metadata,dict)
        ICMetaData._checkMetadata(metadata)
        super().__init__(metadata)
        
    @classmethod
    def loadAny(cls, directory):
        try:
            return ICMetaData.fromTiff(directory)
        except:
            try:
                return ICMetaData.fromOldPWS(directory)
            except:
                raise Exception(f"Could not find a valid PWS image cube file at {directory}.")
                
    @classmethod
    def fromOldPWS(cls,directory):
        try:
            md = json.load(open(os.path.join(directory,'pwsmetadata.txt')))
        except: #have to use the old metadata
            print("Json metadata not found")
            info2 = list(loadmat(os.path.join(directory,'info2.mat'))['info2'].squeeze())
            info3 = list(loadmat(os.path.join(directory,'info3.mat'))['info3'].squeeze())
            wv = list(loadmat(os.path.join(directory,'wv.mat'))['WV'].squeeze())
            wv = [int(i) for i in wv] #We will have issues saving later if these are numpy int types.
            md = {'startWv':info2[0],'stepWv':info2[1],'stopWv':info2[2],
                 'exposure':info2[3],'time':'{:d}-{:d}-{:d} {:d}:{:d}:{:d}'.format(*[int(i) for i in [info3[8],info3[7],info3[6],info3[9],info3[10],info3[11]]]),'systemId':info3[0],
                 'imgHeight':int(info3[2]),'imgWidth':int(info3[3]),'wavelengths':wv}      
        return cls(md)

    @classmethod
    def fromTiff(cls,directory):
        if os.path.exists(os.path.join(directory,'MMStack.ome.tif')):
            path = os.path.join(directory,'MMStack.ome.tif')
        elif os.path.exists(os.path.join(directory,'pws.tif')):
            path = os.path.join(directory,'pws.tif')
        else:
            raise OSError("No Tiff file was found at:", directory)    
        if os.path.exists(os.path.join(directory,'pwsmetadata.json')):
            metadata = json.load(open(os.path.join(directory,'pwsmetadata.json'),'r'))
        else:
            with tf.TiffFile(path) as tif:
                try:
                    metadata = json.loads(tif.pages[0].description)
                except:
                    metadata = json.loads(tif.imagej_metadata['Info']) #The micromanager saves metadata as the info property of the imagej imageplus object.
        metadata['time'] = tif.pages[0].tags['DateTime'].value
        if 'waveLengths' in metadata:
            metadata['wavelengths'] = metadata['waveLengths']
            del metadata['waveLengths']
        return cls(metadata)
    
    def _checkMetadata(metadata):
        required = ['time', 'exposure', 'wavelengths']
        for i in required:
            if i not in metadata:
                raise ValueError(f"Metadata does not have a '{i}' field.")
                
class CameraCorrection(typing.NamedTuple):
    '''linearityCorrection should be list of polynomial coefficients [a,b,c,etc...] in the order a*x + b*x^2 + c*x^3 + etc...'''
    darkCounts: float
    linearityPolynomial: typing.List[float] = None