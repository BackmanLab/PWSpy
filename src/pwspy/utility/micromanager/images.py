import tifffile as tf
from glob import glob
import os

class MMImage:
    def __init__(self, directory: str):
        files = glob(os.path.join(directory, '*MMStack*'))
        self.f = tf.TiffFile(files[0])

    def getPosition(self, x: int, y: int):
        return [im for im in self.f.series if tuple([int(i) for i in im.name.split('-Pos')[-1].split('_')]) == (y,x)][0]

if __name__ == '__main__':
    a=MMImage(r'G:\Data\waterdishcoverage\medconf\fixed_1')
    b=1