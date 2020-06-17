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

import tifffile as tf
from glob import glob
import os


class Image:
    """Represents a multi-file Tiff image saved by Micro-Manager

    Args:
        directory: The file path to the folder containing the Micro-Manager TIFF files.
    """
    def __init__(self, directory: str):
        files = glob(os.path.join(directory, '*MMStack*'))
        self.f = tf.TiffFile(files[0])

    def getPosition(self, x: int, y: int):
        return [im for im in self.f.series if tuple([int(i) for i in im.name.split('-Pos')[-1].split('_')]) == (y, x)][0]

if __name__ == '__main__':
    a = Image(r'G:\Data\waterdishcoverage\medconf\fixed_1')