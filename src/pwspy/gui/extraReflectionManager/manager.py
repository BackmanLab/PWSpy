import json
import os
from glob import glob
import jsonschema
from pwspy import ExtraReflectanceCube


class ERManager:
    _indexSchema = {
        "$schema": "http://json-schema.org/schema#",
       '$id': 'extraReflectionIndexSchema',
       'title': 'extraReflectionIndexSchema',
       'type': 'object',
       'properties': {
           'reflectionCubes': {
               'type': 'array',
               'items': {
                   'type': 'object',
                   'properties': {
                       'fileName': {'type': 'string'},
                       'description': {'type': 'string'},
                       'idTag': {'type': 'string'},
                       'name': {'type': 'string'}
                   },
                   'required': ['fileName', 'description', 'creationDate', 'name']
               }

            }
       }
    }

    def __init__(self, filePath: str):
        self.directory = filePath
        self.auth = None
        self._initialize()

    def _initialize(self):
        with open(os.path.join(self.directory, 'index.json'), 'r') as f:
            self.index = json.load(f)
        jsonschema.validate(self.index, schema=self._indexSchema)
        files = glob(os.path.join(self.directory, f'*{ExtraReflectanceCube.fileSuffix}'))
        files = [(f, ExtraReflectanceCube.validPath(f)) for f in files]  # validPath returns whether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        tags = [ExtraReflectanceCube.getMetadata(directory, name)['idTag'] for directory, name in files]
        for i in self.index['reflectionCubes']:
            i['downloaded'] = i['idTag'] in tags

    def download(self, fileName: str):
        if self.auth is None:
            raise AttributeError("manager Google Drive authentication has not been set.")
