# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 17:27:55 2019

@author: Nick
"""

from pwspy import KCube
from pwspy.imCube.ImCubeClass import FakeCube
import unittest

class myTest(unittest.TestCase):
    def test_load(self):
        try:
            im = FakeCube(1)
            spec, std = im.getMeanSpectra()
        except Exception as e:
            self.fail(f"test_load raised {e}")
    def test_kcube(self):
        try:
            im = FakeCube(2)
            k = KCube(im)
            slope, r2 = k.getAutoCorrelation(True, 100)
        except Exception as e:
            self.fail(f"test_kcube raised {e}")
        

        
if __name__=='__main__':
    unittest.main()