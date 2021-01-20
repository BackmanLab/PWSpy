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

from __future__ import annotations
import json
import logging
import os
from datetime import datetime
from typing import List, Optional, TextIO

import jsonschema

from pwspy import dateTimeFormat


class ERIndex:
    FILENAME = 'index.json'  # TODO replace hardcoded `index.json` throughout the library with a reference to this variable.
    _indexSchema = {
        "$schema": "http://json-schema.org/schema#",
        '$id': 'extraReflectionIndexSchema',
        'title': 'extraReflectionIndexSchema',
        'type': 'object',
        'properties': {
            'reflectanceCubes': {
                'type': 'array',
                'items': {
                    'type': 'object',
                    'properties': {
                        'fileName': {'type': 'string'},
                        'description': {'type': 'string'},
                        'idTag': {'type': 'string'},
                        'name': {'type': 'string'},
                        'md5': {'type': 'string'}
                    },
                    'required': ['fileName', 'description', 'idTag', 'name']
                }
            },
            'creationDate': {'type': 'string'}
        }
    }

    def __init__(self, cubes: List[ERIndexCube], creationDate: Optional[str] = None):
        self.cubes = cubes
        if creationDate is None:
            self.creationDate = datetime.strftime(datetime.now(), dateTimeFormat)
        else:
            self.creationDate = creationDate

    @classmethod
    def load(cls, f: TextIO) -> ERIndex:
        try:
            indexFile = json.load(f)  # For unknown reasons this can sometime raises a JsonDecodeError and the index file needs to be redownloaded.
        except json.JSONDecodeError as e:
            f.seek(0)
            logging.getLogger(__name__).error(f"ERIndex.load() encountered a json.JSONDecodeError. File contents:\n {f.read()}")
            raise e  # Other parts of the application rely on this error to determine what to do.
        jsonschema.validate(indexFile, schema=cls._indexSchema)
        cubes = [ERIndexCube.fromDict(i) for i in indexFile['reflectanceCubes']]
        return cls(cubes, indexFile['creationDate'])

    def toDict(self) -> dict:
        return {'creationDate': self.creationDate, 'reflectanceCubes': [i.toDict() for i in self.cubes]}

    def toJson(self, directory: str):
        with open(os.path.join(directory, self.FILENAME), 'w') as f:
            json.dump(self.toDict(), f, indent=4)

    def getItemFromIdTag(self, idTag: str) -> ERIndexCube:
        for i in self.cubes:
            if i.idTag == idTag:
                return i
        raise ValueError(f"No item with idTag {idTag} was found.")

    @classmethod
    def merge(cls, index1: ERIndex, index2: ERIndex) -> ERIndex:
        """
        Provided two ERIndex objects this method will return a new ERIndex that merges the entries from both indices.
        If both indices contain an ERIndexCube entry that is similar but not identical a value error will be raised.
        Args:
            index1: The first ERIndex object
            index2: The seconds ERIndex object

        Returns:
            A new ERIndex object that combines the entries from both inputs.
        """
        import itertools
        newCubes = []
        idx1Cubes = [cube for cube in index1.cubes]
        idx2Cubes = [cube for cube in index2.cubes]
        for cube in idx1Cubes:
            match = [cube.idTag == c.idTag for c in idx2Cubes]
            if any(match): # The entry exists in both indexes, check for consistency
                matchingCube = next(itertools.compress(idx2Cubes, match))
                if cube != matchingCube:  # The idTags match but the entries are not identical
                    raise ValueError(f"The two indices contain entries that have the same idTags but do not match.")
                else:
                    newCubes.append(cube)
                    idx2Cubes.remove(matchingCube)
            else:  # index1 entry wasn't found in index2
                newCubes.append(cube)
        for cube in idx2Cubes:  # Everything still left in this list should be unique to index 2.
            newCubes.append(cube)
        return ERIndex(newCubes)


class ERIndexCube:
    """Information about a single ExtraReflectance data cube without necesarrily having the data.
    Useful for matching a local datafile/index entry with an online one."""
    def __init__(self, fileName: str, description: str, idTag: str, name: str, md5: Optional[str]):
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.name = name
        self.md5 = md5

    @classmethod
    def fromDict(cls, d: dict) -> ERIndexCube:
        return cls(**d)

    def toDict(self):
        return {'fileName': self.fileName, 'description': self.description, 'idTag': self.idTag, 'name': self.name, 'md5': self.md5}

    def __repr__(self) -> str:
        return str(self.toDict())

    def __eq__(self, other: ERIndex):
        assert isinstance(other, ERIndexCube)
        return self.toDict() == other.toDict()