import h5py

from pwspy.imCube.ICBaseClass import ICBase


def toHdf(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        hf.create_dataset('data', data=cube.data, compression=compression, chunks=True)
        hf.create_dataset('index', data=cube.index)

def toHdf2(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        grp = hf.create_group('data')
        for i, ind in enumerate(cube.index):
            grp.create_dataset(str(ind), cube.data[:, :, i], compression=compression, chunks=True)

def toHdf3(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        hf.create_dataset('data', data=cube.data, compression=compression, chunks=(*cube.data.shape[:2], 1))
        hf.create_dataset('index', data=cube.index)

def toHdf4(cube: ICBase, path: str, compression: int):
    with h5py.File(path, 'w') as hf:
        hf.create_dataset('data', data=cube.data, compression=compression, chunks=(1, 1, cube.data.shape[2]))
        hf.create_dataset('index', data=cube.index)