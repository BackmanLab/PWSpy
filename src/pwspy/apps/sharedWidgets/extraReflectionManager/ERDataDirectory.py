from __future__ import annotations
import hashlib
import os
from enum import Enum
from glob import glob
from typing import List

import pandas, tempfile

from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndex, ERIndexCube
from pwspy.dataTypes import ERMetadata
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
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
        self.rescan()

    @abstractmethod
    def scanIndexFile(self):
        """update self.index from the index file."""
        pass
    
    @abstractmethod
    def rescan(self):
        """Update self.index and self.status from the directory being managed. """
        pass


class ERDataDirectory(ERAbstractDirectory):
    """A class representing the locally stored data file directory for ExtraReflectanceCube files."""
    def __init__(self, directory: str):
        self._directory = directory
        super().__init__()

    def rescan(self):
        """Scan the local files and compare them to the contents of the local index file. store the comparison results in `self.status`."""
        self.index = ERIndex.loadFromFile(os.path.join(self._directory, 'index.json'))
        files = glob(os.path.join(self._directory, f'*{ERMetadata.FILESUFFIX}'))
        files = [(f, ERMetadata.validPath(f)) for f in files]  # validPath returns True/False in awhether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        self.files = [ERMetadata.fromHdfFile(directory, name) for directory, name in files]
        calculatedIndex = self._buildIndexFromFiles(self.files)
        d = self._compareIndexes(calculatedIndex, self.index)
        d = pandas.DataFrame(d).transpose()
        d.columns.values[1] = 'Local Status'
        self.status = d

    @staticmethod
    def _buildIndexFromFiles(files: List[ERMetadata]) -> ERIndex:
        """Scan the data files in the directory and construct an ERIndex from the metadata. The `description` field is left blank though."""
        # TODO This function is quite slow, 1.6 seconds. profile it
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
    def __init__(self, manager: ERManager):
        self._manager = manager
        if self._manager.offlineMode:
            raise Exception("The EROnlineDirectory cannot be used when the ERManager is in offline mode.")
        super().__init__()

    def rescan(self):
        """Compare the status of the online index file and online files. store the results in `self.status`"""
        if self._manager._downloader is not None:
            self._manager._downloader.updateFilesList()
        self.index = self.getIndexFile()
        calculatedIndex = self.buildIndexFromOnlineFiles()
        d2 = self.compareIndexes(calculatedIndex, self.index)
        d2 = pandas.DataFrame(d2).transpose()
        d2.columns.values[1] = 'Online Status'
        self.status = d2

    def getIndexFile(self) -> ERIndex:
        """Return an ERIndex object from the 'index.json' file saved on Google Drive."""
        tempDir = tempfile.mkdtemp()
        indexDir = os.path.join(tempDir, 'index.json')
        if os.path.exists(indexDir):
            os.remove(indexDir)
        try:
            self._manager._downloader.updateFilesList()
            self._manager.download('index.json', tempDir)
        except OfflineError:
            return None
        except ValueError: # File doesn't exist
            print("Index file was not found on google drive. Uploading from local data directory.")
            self._manager.upload(os.path.join(self._manager._directory, 'index.json'))
            time.sleep(3)
            return self.getIndexFile() #Try downloading again.
        index = ERIndex.loadFromFile(indexDir)
        os.remove(indexDir)
        os.rmdir(tempDir)
        return index

    def buildIndexFromOnlineFiles(self) -> ERIndex:
        """Return an ERIndex object from the HDF5 data files saved on Google Drive. No downloading required, just scanning metadata."""
        downloader = self._manager._downloader
        files = downloader.getFolderIdContents(
            downloader.getIdByName('PWSAnalysisAppHostedFiles'))
        files = downloader.getFolderIdContents(
            downloader.getIdByName('ExtraReflectanceCubes', fileList=files))
        files = [f for f in files if ERMetadata.FILESUFFIX in f['name']]  # Select the dictionaries that correspond to a extra reflectance data file
        files = [ERIndexCube(fileName=f['name'], md5=f['md5Checksum'], name=ERMetadata.directory2dirName(f['name'])[-1], description=None, idTag=None) for f in files]
        return ERIndex(files)

    @staticmethod
    def compareIndexes(calculatedIndex: ERIndex, jsonIndex: ERIndex) -> dict:
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
