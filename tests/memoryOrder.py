# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

from timeit import timeit
import os.path as osp
from pwspy.dataTypes import ImCube

resources = osp.join(osp.split(__file__)[0], '_resources')
testCellPath = osp.join(resources, 'Cell1')

im = ImCube.loadAny(testCellPath)
print(im.data.flags)
im.data = im.data.copy(order='F') #This is currently how data is read into the array by default
im2 = ImCube.loadAny(testCellPath)
im2.data = im2.data.copy(order='C')

if __name__ == '__main__':
    print("MemReorder to C")
    print("F: ", timeit(stmt='cube.data.copy(order="C")', setup='from __main__ import im as cube', number=5))
    print("C: ", timeit(stmt='cube.data.copy(order="C")', setup='from __main__ import im2 as cube', number=5))

    print('meanR')
    print('F: ', timeit(stmt='cube.data.mean(axis=2)', setup='from __main__ import  im as cube', number=5))
    print('C: ', timeit(stmt='cube.data.mean(axis=2)', setup='from __main__ import im2 as cube', number=5))

    print('rms')
    print('F: ', timeit(stmt='cube.data.std(axis=2)', setup='from __main__ import im as cube', number=5))
    print('C: ', timeit(stmt='cube.data.std(axis=2)', setup='from __main__ import im2 as cube', number=5))


    print('convert KCUbe and get OPD')
    print('F: ', timeit(stmt='KCube.fromImCube(cube).getOpd(isHannWindow=True, indexOpdStop=100)', setup='from __main__ import KCube, im as cube', number=5))
    print('C: ', timeit(stmt='KCube.fromImCube(cube).getOpd(isHannWindow=True, indexOpdStop=100)', setup='from __main__ import KCube, im2 as cube', number=5))


    print('meanSpectra')
    print('F: ', timeit(stmt='cube.getMeanSpectra()', setup='from __main__ import im as cube', number=5))
    print('C: ', timeit(stmt='cube.getMeanSpectra()', setup='from __main__ import im2 as cube', number=5))

#It appears that C ordering is always better. Reordering takes time. best to save and load in the proper order if possible.