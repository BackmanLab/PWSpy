import h5py

from pwspy.imCube.ICBaseClass import ICBase
import numpy as np


def toHdf(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        hf.create_dataset('data', data=cube.data, compression=compression, chunks=True)
        hf.create_dataset('index', data=cube.index)

def toHdf2(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        grp = hf.create_group('data')
        for i, ind in enumerate(cube.index):
            grp.create_dataset(str(ind), data=cube.data[:, :, i], compression=compression, chunks=True)

def toHdf3(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        hf.create_dataset('data', data=cube.data, compression=compression, chunks=(*cube.data.shape[:2], 1))
        hf.create_dataset('index', data=cube.index)

def toHdf4(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        hf.create_dataset('data', data=cube.data, compression=compression, chunks=(1, 1, cube.data.shape[2]))
        hf.create_dataset('index', data=cube.index)

def toHdf5(cube: ICBase, path: str, compression: int):
    data = np.diff(cube.data, axis=2)
    with h5py.File(path, 'w') as hf:
        hf.create_dataset('data', data=data, compression=compression, chunks=True)
        hf.create_dataset('index', data=cube.index)


def fromHdf(path: str):
    with h5py.File(path, 'r') as f:
        data = np.array(f['data'])
        return ICBase(data, f['index'])

def fromDiffHdf(path: str):
    