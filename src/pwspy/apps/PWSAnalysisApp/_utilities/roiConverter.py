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

import copy
import logging
import os
from typing import List

from pwspy.dataTypes import AcqDir, Roi


class RoiConverter:
    """A class that converts old-style .mat roi files to the newer .h5 files.
    The key difference here is that the new files contain an array of vertices
    that specify the outline of the roi. Without these vertices they must be
    calculated using the concave hull method which is slow."""
    def __init__(self, cells: List[AcqDir]):
        for cell in cells:
            logger = logging.getLogger(__name__)
            logger.info(cell.filePath)
            rois = cell.getRois()
            for name, num, fformat in rois:
                if fformat == Roi.FileFormats.MAT:
                    logger.info('\t', name, num, "MAT")
                    roi = Roi.fromMat(cell.filePath, name, num)
                elif fformat == Roi.FileFormats.HDF:
                    logger.info('\t', name, num, "LegacyHDF")
                    roi = Roi.fromHDF_legacy(cell.filePath, name, num)
                else:
                    logger.info('\t', "Skipping", name, num, fformat.name)
                    continue #Conversion of other formats is not supported
                assert roi.verts is None
                roi.verts = roi.getBoundingPolygon().get_verts()  # Use concave hull method to generate the vertices.
                oldFormat = roi.fileFormat
                oldDirectory = os.path.dirname(roi.filePath)
                Roi.deleteRoi(oldDirectory, roi.name, roi.number, fformat=oldFormat)
                roi.toHDF(cell.filePath)  # save to Roi.FileFormat.HDF2 format. At this point the filePath and fileFormat will be changed. Don't use the delete method or we'll delete the new file.

