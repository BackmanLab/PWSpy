"""Used to translate old fluorescence images to the new file organization that is recognized by the code."""
from glob import glob
from pwspy.dataTypes import FluorescenceImage
import tifffile as tf
import os
import numpy as np

wdir = r'H:\Micropillars_day1_differentsizes_spacings_08_16_19'
rotate = 3 #Number of times to rotate counter-clockwise 90 degrees.
flipX = True
flipY = False

files = glob(os.path.join(wdir, '**', 'FL_Cell*'), recursive=True)
for file in files:
    cellNum = int(file.split('FL_Cell')[-1])
    parentPath = file.split("FL_Cell")[0]
    data = tf.imread(os.path.join(file, 'image_bd.tif'))
    data = np.rot90(data, k=rotate)
    if flipX:
        data = np.flip(data, axis=1)
    if flipY:
        data = np.flip(data, axis=0)
    fl = FluorescenceImage(data, {'exposure': None})
    newPath = os.path.join(parentPath, f'Cell{cellNum}', 'Fluorescence')
    os.mkdir(newPath)
    fl.toTiff(newPath)


