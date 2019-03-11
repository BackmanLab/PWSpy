from timeit import timeit
import os.path as osp
from pwspy import ImCube, KCube

resources = osp.join(osp.split(__file__)[0], 'resources')
testCellPath = osp.join(resources, 'Cell1')

im = ImCube.loadAny(testCellPath)
im.data = im.data.copy(order='F') #This is currently how data is read into the array by default
im2 = ImCube.loadAny(testCellPath)
im2.data = im2.data.copy(order='C')

if __name__ == '__main__':
    print('meanR')
    print('F: ', timeit(stmt='cube.data.mean(axis=2)', setup='from __main__ import  im as cube', number=5))
    print('C: ', timeit(stmt='cube.data.mean(axis=2)', setup='from __main__ import im2 as cube', number=5))

    print('rms')
    print('F: ', timeit(stmt='cube.data.std(axis=2)', setup='from __main__ import im as cube', number=5))
    print('C: ', timeit(stmt='cube.data.std(axis=2)', setup='from __main__ import im2 as cube', number=5))


    print('convert KCUbe and get OPD')
    print('C: ', timeit(stmt='KCube.fromImCube(cube).getOpd(isHannWindow=True, indexOpdStop=100)', setup='from __main__ import KCube, im2 as cube', number=5))
    print('F: ', timeit(stmt='KCube.fromImCube(cube).getOpd(isHannWindow=True, indexOpdStop=100)', setup='from __main__ import KCube, im as cube', number=5))


    print('meanSpectra')
    print('F: ', timeit(stmt='cube.getMeanSpectra()', setup='from __main__ import im as cube', number=5))
    print('C: ', timeit(stmt='cube.getMeanSpectra()', setup='from __main__ import im2 as cube', number=5))

#It appears that C ordering is always better.