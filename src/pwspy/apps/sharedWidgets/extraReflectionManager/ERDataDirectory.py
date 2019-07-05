from __future__ import annotations
import hashlib
import os
from enum import Enum
from glob import glob
from typing import List

import pandas

from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndex, ERIndexCube
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager



class ERDataDirectory:
    class DataStatus(Enum):
        md5Confict = 'Data MD5 mismatch'
        found = 'Found'
        notIndexed = 'Not Indexed'
        missing = 'Data File Missing'

    def __init__(self, directory: str, manager: ERManager):
        self._directory = directory
        self._manager = manager
        self.index: ERIndex = None
        self.rescan()

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
        onlineIndex = self.downloadIndex()
        d2 = self.compareIndexes(self.index, onlineIndex)
        d2 = pandas.DataFrame(d2).transpose()
        d2.columns.values[1] = 'Online Status'
        d = pandas.merge(d, d2, how='outer', on='idTag')
        self.status = d
        self.status = self.status[['idTag', 'Local Status', 'Online Status']]  # Set the column order

    def downloadIndex(self) -> ERIndex:
        tempDir = os.path.join(self._directory, 'temp')
        if not os.path.exists(tempDir):
            os.mkdir(tempDir)
        indexDir = os.path.join(tempDir, 'index.json')
        if os.path.exists(indexDir):
            os.remove(indexDir)
        self._manager.download('index.json', tempDir)
        index = ERIndex.loadFromFile(indexDir)
        os.remove(indexDir)
        os.rmdir(tempDir)
        return index

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
