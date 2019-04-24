import json
import os
from glob import glob
import jsonschema

from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from pwspy.utility.GoogleDriveDownloader import GoogleDriveDownloader

from pwspy import ExtraReflectanceCube
from pwspy.apps.PWSAnalysisApp import applicationVars


class ERManager:
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
                    'required': ['fileName', 'description', 'idTag', 'name', 'md5']
                }
            },
            'creationDate': {'type': 'string'}
        }
    }

    def __init__(self, filePath: str):
        self.directory = filePath
        self.downloader = None
        self.reinitialize()

    def reinitialize(self):
        indexPath = os.path.join(self.directory, 'index.json')
        if not os.path.exists(indexPath):
            self.download('index.json')
        with open(indexPath, 'r') as f:
            self.index = json.load(f)
        jsonschema.validate(self.index, schema=self._indexSchema)
        files = glob(os.path.join(self.directory, f'*{ERMetadata.FILESUFFIX}'))
        files = [(f, ERMetadata.validPath(f)) for f in files]  # validPath returns whether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        tags = [ERMetadata.fromHdfFile(directory, name).idTag for directory, name in files]
        for i in self.index['reflectanceCubes']:
            i['downloaded'] = i['idTag'] in tags

    def download(self, fileName: str):
        if self.downloader is None:
            self.downloader = GoogleDriveDownloader(applicationVars.googleDriveAuthPath)
        files = self.downloader.getFolderIdContents(self.downloader.getIdByName('PWSAnalysisAppHostedFiles'))
        files = self.downloader.getFolderIdContents(self.downloader.getIdByName('ExtraReflectanceCubes', fileList=files))
        fileId = self.downloader.getIdByName(fileName, fileList=files)
        self.downloader.downloadFile(fileId, os.path.join(self.directory, fileName))

    def getMetadataFromId(self, Id: str) -> ERMetadata:
        try:
            match = [item for item in self.index['reflectanceCubes'] if item['idTag'] == Id][0]
        except IndexError:
            raise IndexError(f"An ExtraReflectanceCube with idTag {Id} was not found in the index.json file at {self.directory}.")
        return ERMetadata.fromHdfFile(self.directory, match['name'])



if __name__ == '__main__':
    m = ERManager(applicationVars.extraReflectionDirectory)
