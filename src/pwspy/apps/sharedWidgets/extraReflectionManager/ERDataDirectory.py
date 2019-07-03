import hashlib
import os
from enum import Enum
from glob import glob
from typing import List

import pandas

from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndex, ERIndexCube
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata

class DataStatus(Enum):
    md5Confict = 'Data MD5 mismatch'
    found = 'Found'
    notIndexed = 'Not Indexed'
    missing = 'Data File Missing'


class ERDataDirectory:
    def __init__(self, directory: str):
        self._directory = directory
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
        files = [(f, ERMetadata.validPath(f)) for f in
                 files]  # validPath returns True/False in awhether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        self.files = [ERMetadata.fromHdfFile(directory, name) for directory, name in files]
        calculatedIndex = self.buildIndexFromFiles(self.files)
        foundTags = set([cube.idTag for cube in calculatedIndex.cubes])
        indTags = set([cube.idTag for cube in self.index.cubes])
        notIndexed = foundTags - indTags  # Tags in foundTags but not in indTags
        missing = indTags - foundTags  # Tags in in indTags but not in foundTags
        matched = indTags & foundTags  # Tags present in both sets
        dataMismatch = []  # Tags that match but have different md5 hashes
        for ID in matched:
            cube = [cube for cube in calculatedIndex.cubes if cube.idTag == ID][0]
            indCube = [cube for cube in self.index.cubes if cube.idTag == ID][0]
            if cube.md5 != indCube.md5:
                dataMismatch.append(ID)
        #  Construct a dataframe
        d = {}
        for i, tag, in enumerate(foundTags | indTags):
            if tag in missing:
                status = DataStatus.missing.value
            elif tag in notIndexed:
                status = DataStatus.notIndexed.value
            elif tag in dataMismatch:
                status = DataStatus.md5Confict.value
            elif tag in matched: #it must have been matched.
                status = DataStatus.found.value
            else:
                raise Exception("Programming error.")#This shouldn't be possible
            d[i] = {'idTag': tag, 'status': status}
        self.status = pandas.DataFrame(d).transpose()
        self.status = self.status[['idTag', 'status']] # Set the column order
