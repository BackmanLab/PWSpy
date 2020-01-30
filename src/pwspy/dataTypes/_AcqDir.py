import subprocess
from typing import List, Tuple, Optional

import sys
from ._FluoresenceImg import FluorescenceImage
from pwspy.dataTypes import ICMetaData, DynMetaData
from ._metadata import FluorMetaData
from ._otherClasses import Roi
import os
import numpy as np

from pwspy.utility.misc import cached_property


class AcqDir:
    """This class handles the file structure of a single acquisition. this can include a PWS acquisition as well as colocalized Dynamics and fluorescence.

    Args:
        directory: the file path the root directory of the acquisition
    """
    def __init__(self, directory: str):
        self.filePath = directory
        if (self.pws is None) and (self.dynamics is None): # We must have one of these two items.
            raise OSError(f"Could not find a valid PWS or Dynamics Acquisition at {directory}.")

    @cached_property
    def pws(self) -> Optional[ICMetaData]:
        """ICMetaData: Returns None if no PWS acquisition was found."""
        try:
            return ICMetaData.loadAny(os.path.join(self.filePath, 'PWS'), acquisitionDirectory=self)
        except:
            try:
                return ICMetaData.loadAny(os.path.join(self.filePath), acquisitionDirectory=self) #Many of the old files are saved here in the root directory.
            except:
                return None

    @cached_property
    def dynamics(self) -> Optional[DynMetaData]:
        """DynMetaData: Returns None if no dynamics acquisition was found."""
        try:
            return DynMetaData.fromTiff(os.path.join(self.filePath, 'Dynamics'), acquisitionDirectory=self)
        except:
            try:
                return DynMetaData.fromOldPWS(self.filePath, acquisitionDirectory=self) #This is just for old acquisitions where they were saved in their own folder that was indistinguishable from a PWS acquisitison.
            except:
                return None

    @cached_property
    def fluorescence(self) -> FluorMetaData:
        path = os.path.join(self.filePath, 'Fluorescence')
        try:
            return FluorMetaData.fromTiff(path, acquisitionDirectory=self)
        except ValueError:
            return None

    @property
    def idTag(self):
        if self.pws is not None:
            return self.pws.idTag
        else: #We must have one of these two items.
            return self.dynamics.idTag

    def getRois(self) -> List[Tuple[str, int, Roi.FileFormats]]:
        """Return information about the Rois found in the acquisition's file path.
        See documentation for Roi.getValidRoisInPath()"""
        assert self.filePath is not None
        return Roi.getValidRoisInPath(self.filePath)

    def loadRoi(self, name: str, num: int, fformat: Roi.FileFormats = None) -> Roi:
        """Load a Roi that has been saved to file in the acquisition's file path."""
        assert isinstance(name, str)
        assert isinstance(num, int)
        if fformat == Roi.FileFormats.MAT:
            return Roi.fromMat(self.filePath, name, num)
        elif fformat == Roi.FileFormats.HDF2:
            return Roi.fromHDF(self.filePath, name, num)
        elif fformat == Roi.FileFormats.HDF:
            return Roi.fromHDF_legacy(self.filePath, name, num)
        else:
            return Roi.loadAny(self.filePath, name, num)

    def saveRoi(self, roi: Roi, overwrite: bool = False) -> None:
        """Save a Roi to file in the acquisition's file path."""
        roi.toHDF(self.filePath, overwrite=overwrite)

    def deleteRoi(self, name: str, num: int):
        Roi.deleteRoi(self.filePath, name, num)

    def editNotes(self):
        """Create a `notes.txt` file if it doesn't already exists and open it in a text editor."""
        filepath = os.path.join(self.filePath, 'notes.txt')
        if not os.path.exists(filepath):
            with open(filepath, 'w') as f:
                pass
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name == 'nt':  # For Windows
            os.startfile(filepath)
        elif os.name == 'posix':  # For Linux, Mac, etc.
            subprocess.call(('xdg-open', filepath))

    def hasNotes(self) -> bool:
        """Indicates whether or not a `notes.txt` file was found."""
        return os.path.exists(os.path.join(self.filePath, 'notes.txt'))

    def getNotes(self) -> str:
        """Return the contents of `notes.txt` as a string."""
        if self.hasNotes():
            with open(os.path.join(self.filePath, 'notes.txt'), 'r') as f:
                return '\n'.join(f.readlines())
        else:
            return ''

    def getThumbnail(self) -> np.ndarray:
        """Return a thumbnail from any of the available acquisitions. Should be an 8bit normalized image."""
        if self.pws is not None:
            return self.pws.getThumbnail()
        elif self.dynamics is not None:
            return self.dynamics.getThumbnail()
        elif self.fluorescence is not None:
            return self.fluorescence.getThumbnail()
