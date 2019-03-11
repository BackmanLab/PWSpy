import tifffile as tf
from timeit import timeit
import os.path as osp


def arrayOrder():
    t = tf.TiffFile()


if __name__ == '__main__':
    timeit(stmt='arrayOrder()', setup='from __main__ import arrayOrder', number=100)
