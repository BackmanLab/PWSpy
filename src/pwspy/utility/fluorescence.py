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

"""
Functions related to fluorescent images.

Functions
-----------
.. autosummary::
   :toctree: generated/

   updateFolderStructure

"""

import os
from glob import glob
import numpy as np
import tifffile as tf
import pwspy.dataTypes as pwsdt


def updateFolderStructure(rootDirectory: str, rotate: int, flipX: bool, flipY: bool):
    """Used to translate old fluorescence images to the new file organization that is recognized by the code.

    Args:
        rootDirectory: The top level directory containing fluorescence images that were saved in the old `FL_Cell{X}` folder format
        rotate: The number of times that the images should be rotated clockwise to match up with the PWS images they go with
        flipX: Should the images be mirrored over the X-axis after being rotated?
        flipY: Should the images be mirrored over the Y-axis after being rotated?

    """

    files = glob(os.path.join(rootDirectory, '**', 'FL_Cell*'), recursive=True)
    for file in files:
        cellNum = int(file.split('FL_Cell')[-1])
        parentPath = file.split("FL_Cell")[0]
        data = tf.imread(os.path.join(file, 'image_bd.tif'))
        data = np.rot90(data, k=rotate)
        if flipX:
            data = np.flip(data, axis=1)
        if flipY:
            data = np.flip(data, axis=0)
        fl = pwsdt.FluorescenceImage(data, {'exposure': None})
        newPath = os.path.join(parentPath, f'Cell{cellNum}', 'Fluorescence')
        os.mkdir(newPath)
        fl.toTiff(newPath)
