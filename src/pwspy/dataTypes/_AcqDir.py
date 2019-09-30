import subprocess
from typing import List, Tuple

import sys
from ._FluoresenceImg import FluorescenceImage
from dataTypes._metadata._ICMetaDataClass import ICMetaData
from dataTypes._metadata._DynMetaDataClass import DynMetaData
from ._otherClasses import Roi
import os

from pwspy.utility.misc import cached_property


class AcqDir:
    """"A class handling the file structure of a single acquisition. this can include a PWS acquisition as well as collocalized Dynamics and fluorescence."""
    def __init__(self, directory: str):
        self.filePath = directory
        if (self.pws is None) and (self.dynamics is None): # We must have one of these two items.
            raise OSError("Could not find a valid PWS or Dynamics Acquisition.")

    @cached_property
    def pws(self) -> ICMetaData:
        """Returns None of the path was invalid."""
        try:
            return ICMetaData.loadAny(os.path.join(self.filePath, 'PWS'), acquisitionDirectory=self)
        except:
            try:
                return ICMetaData.loadAny(os.path.join(self.filePath), acquisitionDirectory=self) #Many of the old files are saved here.
            except:
                return None

    @cached_property
    def dynamics(self) -> DynMetaData:
        try:
            return DynMetaData.fromTiff(os.path.join(self.filePath, 'Dynamics'), acquisitionDirectory=self)
        except:
            return None

    @cached_property
    def fluorescence(self) -> FluorescenceImage:
        path = os.path.join(self.filePath, 'Fluorescence')
        if FluorescenceImage.isValidPath(path):
            return FluorescenceImage.fromTiff(path, acquisitionDirectory=self)
        else:
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