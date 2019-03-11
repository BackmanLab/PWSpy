from timeit import timeit
import os.path as osp
from pwspy import ImCube
from pwspy.utility.io import toHdf, toHdf2, toHdf3, toHdf4, toHdf5, fromHdf, fromDiffHdf
import os
import pprint

pp = pprint.PrettyPrinter(indent=4)

resources = osp.join(osp.split(__file__)[0], 'resources')
testCellPath = osp.join(resources, 'Cell1')
savePath = osp.join(resources, 'testCube.h5')

im = ImCube.loadAny(testCellPath)
compression: int = 3

def compareCompression(saver, loader=None):
    #uncompressed
    saveTime = timeit(lambda: saver(im, savePath, compression=None), setup='from __main__ import savePath, im', number=1)
    saveSize = osp.getsize(savePath) / 1e6
    if loader:
        loadTime = timeit(lambda: loader(savePath), number=1)
    else:
        loadTime = None
    os.remove(savePath)

    csaveTime = timeit(lambda: saver(im, savePath, compression=3), setup='from __main__ import savePath, im', number=1)
    csaveSize = osp.getsize(savePath) / 1e6
    if loader:
        cloadTime = timeit(lambda: loader(savePath), number=1)
    else:
        cloadTime = None
    os.remove(savePath)

    ratio = csaveSize/saveSize

    return {'saveTime': saveTime,
            'saveSize': saveSize,
            'loadTime': loadTime,
            'csaveTime': csaveTime,
            'csaveSize': csaveSize,
            'cloadTime': cloadTime,
            'ratio': ratio}

if __name__ == '__main__':
    pass
    pp.pprint(compareCompression(toHdf, fromHdf)) #This appears best.


    # pp.pprint(compareCompression(toHdf3))


    # pp.pprint(compareCompression(toHdf4)) #this appears to be terrible

    pp.pprint(compareCompression(toHdf5, fromDiffHdf))

    # pp.pprint(compareCompression(toHdf6, fromHdf))
