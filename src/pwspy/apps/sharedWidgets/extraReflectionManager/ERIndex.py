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
import os
from datetime import datetime
from typing import List, Optional, TextIO

import jsonschema

from pwspy import dateTimeFormat


class ERIndex:
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
        indexFile = json.load(f)
        jsonschema.validate(indexFile, schema=cls._indexSchema)
        cubes = [ERIndexCube.fromDict(i) for i in indexFile['reflectanceCubes']]
        return cls(cubes, indexFile['creationDate'])

    def toDict(self) -> dict:
        return {'creationDate': self.creationDate, 'reflectanceCubes': [i.toDict() for i in self.cubes]}

    def getItemFromIdTag(self, idTag: str) -> ERIndexCube:
        for i in self.cubes:
            if i.idTag == idTag:
                return i
        raise ValueError(f"No item with idTag {idTag} was found.")


class ERIndexCube:
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