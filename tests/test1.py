# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 17:27:55 2019

@author: Nick
"""

from pwspython import ImCube, KCube
import numpy as np
import unittest

class myTest(unittest.TestCase):
    def setUp(self):
        self.data = np.ones((400,400,100)) * np.sin(np.linspace(0,6,num=100))[np.newaxis,np.newaxis,:]
        #data = np.random.rand(400,400,100)
        wavelengths = np.linspace(500,700, num = self.data.shape[2])
        self.md = ImCube.Metadata({'wavelengths':wavelengths,
                 'exposure':59,
                 'time': "1/2/2019 12:53:57"
                 })
    def test_load(self):
        try:
            im = ImCube(self.data, self.md)
        except Exception as e:
            self.fail(f"test_load raised {e}")
    def test_kcube(self):
        try:
            im = ImCube(self.data, self.md)
            k = KCube(im)
        except Exception as e:
            self.fail(f"test_kcube raised {e}")
        

        
if __name__=='__main__':
    unittest.main()

#im.filterDust(5)
#k.filterDust(5)

#rms1 = np.sqrt(np.sum(im.data**2,axis=2)/im.data.shape[2])
#opd = k.getOpd(False)[0]
#rms2 = np.sqrt(np.sum(opd**2, axis=2) * len(k.wavenumbers) / opd.shape[2])
#
#print(np.max((rms1-rms2)/rms1)*100, '% Error')

