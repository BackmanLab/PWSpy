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

# -*- coding: utf-8 -*-
"""
This script blurs an image cube in the xy direction. Allows you to turn an
image of cells into something that can be used as a reference image, assuming
most of the the FOV is glass.
"""

import copy

import matplotlib.pyplot as plt
from pwspy.dataTypes import ImCube


if __name__ == '__main__':
    a = ImCube.fromTiff(r'G:\Vasundhara_MSCs_data\Cell1170')

    mirror = copy.deepcopy(a)  # This doesn't work right. maybe becuaes of the wi
    mirror.filterDust(10)

    a.plotMean()
    mirror.plotMean()
    norm = (a / mirror)
    norm.plotMean()
    plt.figure()
    plt.imshow(norm.data.std(axis=2))
