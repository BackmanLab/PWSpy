# -*- coding: utf-8 -*-
"""
Created on Tue Aug  7 13:20:25 2018

@author: Nick
"""
import json
from scipy.io import loadmat
import os
import numpy as np

def loadOldPWS(directory):
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
    return data,md