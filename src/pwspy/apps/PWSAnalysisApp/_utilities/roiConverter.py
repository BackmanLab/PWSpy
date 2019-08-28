import copy
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
            print(cell.filePath)
            rois = cell.getRois()
            for name, num, fformat in rois:
                if fformat == Roi.FileFormats.MAT:
                    print('\t', name, num, "MAT")
                    roi = Roi.fromMat(cell.filePath, name, num)
                elif fformat == Roi.FileFormats.HDF:
                    print('\t', name, num, "LegacyHDF")
                    roi = Roi.fromHDF_legacy(cell.filePath, name, num)
                else:
                    continue #Conversion of other formats is not supported
                assert roi.verts is None
                roi.verts = roi.getBoundingPolygon().get_verts()  # Use concave hull method to generate the vertices.
                oldFilePath = roi.filePath
                roi.toHDF(cell.filePath)  # save to hdf. At this point the filePath and fileFormat will be changed. Don't use the delete method or we'll delete the new file.
                Roi.deleteRoi(oldFilePath, roi.name, roi.number)

