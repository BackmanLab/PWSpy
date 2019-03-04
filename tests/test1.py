# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 17:27:55 2019

@author: Nick
"""

from pwspy import KCube, ImCube, CameraCorrection
import unittest
import os.path as osp

from pwspy.imCube.ICMetaDataClass import ICMetaData

resources = osp.join(osp.split(__file__)[0], 'resources')
testCellPath = osp.join(resources, 'Cell1')


class myTest(unittest.TestCase):
    def test_process(self):
        try:
            im = ImCube.loadAny(testCellPath)
            im.filterDust(4)
            im.correctCameraEffects(CameraCorrection(2000, [1, 2, 3]))
            spec, std = im.getMeanSpectra()
        except Exception as e:
            self.fail(f"test_process raised {e}")

    def test_meta(self):
        try:
            im = ImCube.loadAny(osp.join(resources, "Cell1"))
            print(im.getMasks())
            im.loadMask(1, 'nuc')
            im.toJson(testCellPath)
        except Exception as e:
            self.fail(f'test_meta raised {e}')

    def test_kcube(self):
        try:
            im = ImCube.loadAny(testCellPath)
            k = KCube(im)
            slope, r2 = k.getAutoCorrelation(True, 100)
        except Exception as e:
            self.fail(f"test_kcube raised {e}")

        
if __name__ == '__main__':
    unittest.main()
