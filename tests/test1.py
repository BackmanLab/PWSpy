# -*- coding: utf-8 -*-
"""
Created on Sat Feb  9 17:27:55 2019

@author: Nick
"""

from pwspy import KCube, ImCube, CameraCorrection
import unittest
import os.path as osp
import os
from pwspy.utility.micromanager.positions import PositionList, Position2d

resources = osp.join(osp.split(__file__)[0], 'resources')
testCellPath = osp.join(resources, 'Cell1')
posListPath = osp.join(resources, 'testPositions.pos')


class myTest(unittest.TestCase):
    def test_process(self):
        try:
            im = ImCube.loadAny(testCellPath)
            im.filterDust(4)
            im.correctCameraEffects(CameraCorrection(2000, (1, 2, 3)), binning=1)
            spec, std = im.getMeanSpectra()
        except Exception as e:
            self.fail(f"test_process raised {e}")

    def test_meta(self):
        try:
            im = ImCube.loadAny(testCellPath)
            print(im.getRois())
            im.loadRoi('nuc', 1)
            im.metadataToJson(testCellPath)
        except Exception as e:
            self.fail(f'test_meta raised {e}')

    def test_kcube(self):
        try:
            im = ImCube.loadAny(testCellPath)
            k = KCube.fromImCube(im)
            slope, r2 = k.getAutoCorrelation(True, 100)
        except Exception as e:
            self.fail(f"test_kcube raised {e}")

    def test_posList(self):
        try:
            pos = PositionList.load(posListPath)
            pos2 = pos.copy()
            pos2.mirrorX()
            pos2.mirrorY()
            origin = Position2d(75, 50)
            pos2 -= origin
            pos2.save(osp.join(resources, 'tempPList.pos'))
            pos3 = PositionList.load(osp.join(resources, 'tempPList.pos'))
            os.remove(osp.join(resources, 'tempPList.pos'))
            self.assertEqual(pos2, pos3)
            pos3 += origin
            pos3.mirrorY()
            pos3.mirrorX()
            self.assertEqual(pos, pos3)
        except Exception as e:
            self.fail(f'test_posList raised {e}')
        
if __name__ == '__main__':
    unittest.main()
