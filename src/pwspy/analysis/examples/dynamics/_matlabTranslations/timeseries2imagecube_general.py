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

from pwspy.dataTypes import DynCube
import h5py

outPath = r''
refPath = r''

ref = DynCube.loadAny(refPath)
ref.data[:, :, :] = ref.data.mean(axis=2)[:, :, None] #The reference should be static over time. Take the mean to filter out all noise.
#TODO we should save or report the noise level as well.
with h5py.File("outputRef.h5py", 'w') as f:
    ref.toHdfDataset(f, outPath)
