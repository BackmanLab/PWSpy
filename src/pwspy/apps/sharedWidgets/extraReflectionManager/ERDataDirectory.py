from __future__ import annotations
import hashlib
import os, io
from enum import Enum
from glob import glob
from typing import List

import pandas, tempfile

from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndex, ERIndexCube
from pwspy.dataTypes import ERMetadata
import typing

from pwspy.utility import GoogleDriveDownloader

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager, ERDownloader
from .exceptions import OfflineError
from abc import ABC, abstractmethod
import time

class ERAbstractDirectory(ABC):
    """This class keeps track of the status of a directory that contains our extra reflection subtraction cubes.
    This can be a local directory on a hard drive or a folder on Google Drive, etc."""

    class DataStatus(Enum):
        md5Confict = 'Data MD5 mismatch'
        found = 'Found'
        notIndexed = 'Not Indexed'
        missing = 'Data File Missing'

    def __init__(self):
        self.index: ERIndex = None
        self.status: pandas.DataFrame = None
        self.updateIndex()

    @abstractmethod
    def updateIndex(self):
        """update self.index from the `index.json` file."""
        pass

    @abstractmethod
    def updateStatusFromFiles(self):
        """Update self.status by scanning the files in the directory being managed. Assumes that self.index is
        already up to date. In theory the `index.json` file has all the info we need, this method verifies that the
        `index.json` file is actually accurate."""
        pass


class ERDataDirectory(ERAbstractDirectory):
    """A class representing the locally stored data file directory for ExtraReflectanceCube files."""
    def __init__(self, directory: str):
        self._directory = directory
        super().__init__()

    def updateIndex(self):
        with open(os.path.join(self._directory, 'index.json'), 'r') as f:
            self.index = ERIndex.load(f)

    def updateStatusFromFiles(self):
        files = glob(os.path.join(self._directory, f'*{ERMetadata.FILESUFFIX}'))
        files = [(f, ERMetadata.validPath(f)) for f in files]  # validPath returns True/False in awhether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]  # Get rid of invalid files.
        files = [ERMetadata.fromHdfFile(directory, name) for directory, name in files]
        calculatedIndex = self._buildIndexFromFiles(files)
        d = self._compareIndexes(calculatedIndex, self.index)
        d = pandas.DataFrame(d).transpose()
        d.columns.values[1] = 'Local Status'
        self.status = d

    @staticmethod
    def _buildIndexFromFiles(files: List[ERMetadata]) -> ERIndex:
        """Scan the data files in the directory and construct an ERIndex from the metadata. The `description` field is left blank though."""
        # TODO This function is quite slow, 1.6 seconds. Maybe we don't need to be MD5ing the whole file, maybe no md5 at all?
        cubes = []
        for erCube in files:
            md5hash = hashlib.md5()
            with open(erCube.filePath, 'rb') as f:
                md5hash.update(f.read())
            md5 = md5hash.hexdigest()  # The md5 checksum as a string of hex.
            cubes.append(ERIndexCube(erCube.filePath, erCube.inheritedMetadata['description'], erCube.idTag,
                                     erCube.directory2dirName(erCube.filePath)[-1], md5))
        return ERIndex(cubes)

    @staticmethod
    def _compareIndexes(ind1: ERIndex, ind2: ERIndex) -> dict:
        """A utility function to compare two `ERIndex` objects and return a `dict` containing the status for each file. """
        foundTags = set([cube.idTag for cube in ind1.cubes])
        indTags = set([cube.idTag for cube in ind2.cubes])
        notIndexed = foundTags - indTags  # Tags in foundTags but not in indTags
        missing = indTags - foundTags  # Tags in in indTags but not in foundTags
        matched = indTags & foundTags  # Tags present in both sets
        dataMismatch = []  # Tags that match but have different md5 hashes
        for ID in matched:
            cube = [cube for cube in ind1.cubes if cube.idTag == ID][0]
            indCube = [cube for cube in ind2.cubes if cube.idTag == ID][0]
            if cube.md5 != indCube.md5:
                dataMismatch.append(ID)
        # Construct a dataframe
        d = {}
        for i, tag, in enumerate(foundTags | indTags):
            if tag in missing:
                status = ERDataDirectory.DataStatus.missing.value
            elif tag in notIndexed:
                status = ERDataDirectory.DataStatus.notIndexed.value
            elif tag in dataMismatch:
                status = ERDataDirectory.DataStatus.md5Confict.value
            elif tag in matched:  # it must have been matched.
                status = ERDataDirectory.DataStatus.found.value
            else:
                raise Exception("Programming error.")  # This shouldn't be possible
            d[i] = {'idTag': tag, 'status': status}
        return d


class EROnlineDirectory(ERAbstractDirectory):
    """A class representing the status of the google drive directory"""
    def __init__(self, downloader: ERDownloader):
        self._downloader = downloader
        super().__init__()

    def updateIndex(self):
        with io.StringIO() as f:
            self._downloader.downloadToRam('index.json', f)
            self.index = ERIndex.load(f)
        # tempDir = tempfile.mkdtemp()
        # indexPath = os.path.join(tempDir, 'index.json')
        # try:
        #     self._downloader.download('index.json', indexPath)
        #     index = ERIndex.loadFromFile(indexPath)
        #     self.index = index
        # finally:
        #     if os.path.exists(indexPath):
        #         os.remove(indexPath)
        #     os.rmdir(tempDir)

    def updateStatusFromFiles(self):
        calculatedIndex = self._buildIndexFromOnlineFiles()
        d2 = self._compareIndexes(calculatedIndex, self.index)
        d2 = pandas.DataFrame(d2).transpose()
        d2.columns.values[1] = 'Online Status'
        self.status = d2

    def _buildIndexFromOnlineFiles(self) -> ERIndex:
        """Return an ERIndex object from the HDF5 data files saved on Google Drive. No downloading required, just scanning metadata."""
        files = self._downloader.getFileMetadata()
        files = [f for f in files if ERMetadata.FILESUFFIX in f['name']]  # Select the dictionaries that correspond to a extra reflectance data file
        files = [ERIndexCube(fileName=f['name'], md5=f['md5Checksum'], name=ERMetadata.directory2dirName(f['name'])[-1], description=None, idTag=None) for f in files]
        return ERIndex(files)

    @staticmethod
    def _compareIndexes(calculatedIndex: ERIndex, jsonIndex: ERIndex) -> dict:
        """A utility function to compare two `ERIndex` objects and return a `dict` containing the status for each file.
        In this case we are not able to extract the idTags from the dataFiles without downloading them. use filenames instead"""
        foundNames = set([cube.fileName for cube in calculatedIndex.cubes])
        indNames = set([cube.fileName for cube in jsonIndex.cubes])
        notIndexed = foundNames - indNames  # fileNames in foundNames but not in indNames
        missing = indNames - foundNames  # fileNames in in indNames but not in foundNames
        matched = indNames & foundNames  # fileNames present in both sets
        dataMismatch = []  # fileNames that match but have different md5 hashes
        for name in matched:
            cube = [cube for cube in calculatedIndex.cubes if cube.fileName == name][0]
            indCube = [cube for cube in jsonIndex.cubes if cube.fileName == name][0]
            if cube.md5 != indCube.md5:
                dataMismatch.append(name)
        #  Construct a dataframe
        d = {}
        for i, fileName, in enumerate(foundNames | indNames):
            if fileName in missing:
                status = ERDataDirectory.DataStatus.missing.value
            elif fileName in notIndexed:
                status = ERDataDirectory.DataStatus.notIndexed.value
            elif fileName in dataMismatch:
                status = ERDataDirectory.DataStatus.md5Confict.value
            elif fileName in matched:  # it must have been matched.
                status = ERDataDirectory.DataStatus.found.value
            else:
                raise Exception("Programming error.")  # This shouldn't be possible
            d[i] = {'idTag': [ind.idTag for ind in jsonIndex.cubes if ind.fileName == fileName][0], 'status': status}
        return d
