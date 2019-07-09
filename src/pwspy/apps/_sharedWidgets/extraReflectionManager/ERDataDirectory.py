from __future__ import annotations
import hashlib
import os
from enum import Enum
from glob import glob
from typing import List

import pandas, tempfile

from pwspy.apps._sharedWidgets.extraReflectionManager.ERIndex import ERIndex, ERIndexCube
from pwspy.dataTypes._ExtraReflectanceCubeClass import ERMetadata
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps._sharedWidgets.extraReflectionManager import ERManager
from abc import ABC
import time

class ERAbstractDirectory(ABC):
    class DataStatus(Enum):
        md5Confict = 'Data MD5 mismatch'
        found = 'Found'
        notIndexed = 'Not Indexed'
        missing = 'Data File Missing'

    def __init__(self):
        self.index: ERIndex = None
        self.status: pandas.DataFrame = None
        self.rescan()

class ERDataDirectory(ERAbstractDirectory):
    """A class representing the locally stored data file directory for ExtraReflectanceCube files."""
    def __init__(self, directory: str, manager: ERManager):
        self._directory = directory
        self._manager = manager
        super().__init__()

    @staticmethod
    def buildIndexFromFiles(files: List[ERMetadata]) -> ERIndex:
        """Scan the data files in the directory and construct and ERIndex from the metadata. The `description` field is left blank though."""
        cubes = []
        for erCube in files:
            md5hash = hashlib.md5()
            with open(erCube.filePath, 'rb') as f:
                md5hash.update(f.read())
            md5 = md5hash.hexdigest()  # The md5 checksum as a string of hex.
            cubes.append(ERIndexCube(erCube.filePath, erCube.inheritedMetadata['description'], erCube.idTag, erCube.directory2dirName(erCube.filePath)[-1], md5))
        return ERIndex(cubes)

    def rescan(self):
        self.index = ERIndex.loadFromFile(os.path.join(self._directory, 'index.json'))
        files = glob(os.path.join(self._directory, f'*{ERMetadata.FILESUFFIX}'))
        files = [(f, ERMetadata.validPath(f)) for f in files]  # validPath returns True/False in awhether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        self.files = [ERMetadata.fromHdfFile(directory, name) for directory, name in files]
        calculatedIndex = self.buildIndexFromFiles(self.files)
        d = self.compareIndexes(calculatedIndex, self.index)
        d = pandas.DataFrame(d).transpose()
        d.columns.values[1] = 'Local Status'
        self.status = d

    @staticmethod
    def compareIndexes(ind1: ERIndex, ind2: ERIndex) -> dict:
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
        #  Construct a dataframe
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
        super().__init__()

    def rescan(self):
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
            self._manager.download('index.json', tempDir)
        except ValueError: # File doesn't exist
            print("Index file was not found on google drive. Uploading from local data directory.")
            self._manager.upload(os.path.join(self._manager._directory, 'index.json'))
            time.sleep(3)
        index = ERIndex.loadFromFile(indexDir)
        os.remove(indexDir)
        os.rmdir(tempDir)
        return index

    def buildIndexFromOnlineFiles(self) -> ERIndex:
        """Return an ERIndex object from the HDF5 data files saved on Google Drive. No downloading required, just scanning metadata."""
        # api = self._manager._downloader.api
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
        """In this case we are not able to extract the idTags from the dataFiles without downloading them. use filenames instead"""
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
