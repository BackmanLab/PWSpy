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
from pwspy.utility.micromanager import PropertyMap

from pwspy.utility.micromanager.positions import PositionList

"""This example demonstrates how to use generate new cell positions from a set of positions after the sample has been picked up and likely shifted or rotated.
This method relies on measuring a set (at least 3) of reference positions before and after moving the dish. You can then use these positions to generate an 
affine transform. This affine transform can then be applied to your original cell positions in order to generate a new set of positions for the same cells.
In the case of a standard cell culture dish it is best to use the corners of the glass coverslip as your reference locations.
"""

if __name__ == '__main__':

    import pathlib as pl
    import matplotlib.pyplot as plt
    plt.ion()
    NCPath = pl.Path(r'Z:\Nick\NU-NC_EtOH fixation comparison\NC\Buccal cell')
    NUPath = pl.Path(r'Z:\Nick\NU-NC_EtOH fixation comparison\NU\Buccal')

    preTreatRefPositions = PositionList.fromNanoMatFile(NCPath / 'corners_list2.mat', 'TIXYDrive')  # Load the position list of the coverslip corners taken at the beginning of the experiment.
    postTreatRefPositions = PositionList.fromPropertyMap(PropertyMap.loadFromFile(NUPath / 'corners.pos')) # Load the position list of the coverslip corners after placing the dish back on the microscope after treatment.
    transformMatrix = preTreatRefPositions.getAffineTransform(postTreatRefPositions)  # Generate an affine transform describing the difference between the two position lists.
    preTreatCellPositions = PositionList.fromNanoMatFile(NCPath / 'cell_list.mat', 'TIXYDrive')  # Load the positions of the cells we are measuring before the dish was removed.
    postTreatCellPositions = preTreatCellPositions.applyAffineTransform(transformMatrix)  # Transform the cell positions to the new expected locations.
    postTreatCellPositions.toPropertyMap().saveToFile(NUPath / 'transformedPositions.pos')  # Save the new positions to a file that can be loaded by Micro-Manager.

    preTreatRefPositions.plot()
    postTreatRefPositions.plot()
    a = 1
