from datetime import datetime
import hashlib
import json
import os
from glob import glob
from typing import Optional

import jsonschema
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QThread
from PyQt5.QtWidgets import QMessageBox, QApplication, QWidget
from googleapiclient.http import MediaIoBaseDownload

from pwspy.apps.PWSAnalysisApp.sharedWidgets.dialogs import BusyDialog
from pwspy.moduleConsts import dateTimeFormat
from .ERSelectorWindow import ERSelectorWindow
from .ERUploaderWindow import ERUploaderWindow
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from pwspy.utility.GoogleDriveDownloader import GoogleDriveDownloader

from pwspy.imCube import ExtraReflectanceCube
from pwspy.apps.PWSAnalysisApp import applicationVars


class ERManager:
    def __init__(self, filePath: str):
        self._directory = filePath
        self._downloader = None
        self.reinitialize()

    def createSelectorWindow(self, parent: QWidget):
        return ERSelectorWindow(self, parent)

    def createManagerWindow(self, parent: QWidget):
        return ERUploaderWindow(self, parent)

    def reinitialize(self):
        indexPath = os.path.join(self._directory, 'index.json')
        if not os.path.exists(indexPath):
            self.download('index.json')
        with open(indexPath, 'r') as f:
            self.index = json.load(f)
        jsonschema.validate(self.index, schema=self._indexSchema)
        files = glob(os.path.join(self._directory, f'*{ERMetadata.FILESUFFIX}'))
        files = [(f, ERMetadata.validPath(f)) for f in files]  # validPath returns whether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        tags = [ERMetadata.fromHdfFile(directory, name).idTag for directory, name in files]
        for i in self.index['reflectanceCubes']:
            i['downloaded'] = i['idTag'] in tags

    def download(self, fileName: str):
        """Begin downloading `fileName` in a separate thread. Use the main thread to update a progress bar"""
        if self._downloader is None:
            self._downloader = _QtGoogleDriveDownloader(applicationVars.googleDriveAuthPath)
        t = _DownloadThread(self._downloader, fileName, self._directory)
        b = BusyDialog(QApplication.instance().window, f"Downloading {fileName}. Please Wait...", progressBar=True)
        t.finished.connect(b.accept)
        self._downloader.progress.connect(b.setProgress)
        t.errorOccurred.connect(lambda e: QMessageBox.information(QApplication.instance().window, 'Uh Oh', str(e))) #TODO This assumes the main window of the application is .window
        t.start()
        b.exec()


    def getMetadataFromId(self, Id: str) -> ERMetadata:
        """Given the Id string for ExtraReflectanceCube this will search the index.json and return the ERMetadata file"""
        try:
            match = [item for item in self.index['reflectanceCubes'] if item['idTag'] == Id][0]
        except IndexError:
            raise IndexError(f"An ExtraReflectanceCube with idTag {Id} was not found in the index.json file at {self._directory}.")
        return ERMetadata.fromHdfFile(self._directory, match['name'])


class _DownloadThread(QThread):
    """A QThread to download from google drive"""
    errorOccurred = QtCore.pyqtSignal(Exception)
    def __init__(self, downloader, fileName, directory):
        super().__init__()
        self.downloader = downloader
        self.fileName = fileName
        self.directory = directory
    def run(self):
        try:
            files = self.downloader.getFolderIdContents(
                self.downloader.getIdByName('PWSAnalysisAppHostedFiles'))
            files = self.downloader.getFolderIdContents(
                self.downloader.getIdByName('ExtraReflectanceCubes', fileList=files))
            fileId = self.downloader.getIdByName(self.fileName, fileList=files)
            self.downloader.downloadFile(fileId, os.path.join(self.directory, self.fileName))
        except Exception as e:
            self.errorOccurred.emit(e)

class _QtGoogleDriveDownloader(GoogleDriveDownloader, QObject):
    """Same as the standard google drive downloader except it emits a progress signal after each chunk downloaded."""
    progress = QtCore.pyqtSignal(int)
    def __init__(self, authPath: str):
        GoogleDriveDownloader.__init__(self, authPath)
        QObject.__init__(self)

    def downloadFile(self, Id: int, savePath: str):
        """Save the file with `id` to `savePath`"""
        fileRequest = self.api.files().get_media(fileId=Id)
        with open(savePath, 'wb') as f:
            downloader = MediaIoBaseDownload(f, fileRequest)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                self.progress.emit(int(status.progress() * 100))

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
                    'required': ['fileName', 'description', 'idTag', 'name', 'md5']
                }
            },
            'creationDate': {'type': 'string'}
        }
    }
    def __init__(self, cubes: ERIndexCube, creationDate: Optional[str] = None):
        self.cubes = cubes
        if creationDate is None:
            self.creationDate = datetime.strftime(datetime.now(), dateTimeFormat)
        else:
            self.creationDate = creationDate

    @classmethod
    def loadFromFile(cls, filePath: str) -> ERIndex:
        os.path.exists(filePath)
        with open(filePath, 'r') as f:
            indexFile = json.load(f)
        jsonschema.validate(indexFile, schema=cls._indexSchema)
        cubes = [ERIndexCube.fromDict(i) for i in indexFile['reflectanceCubes']]
        return cls(cubes, indexFile['creationDate'])

    def toDict(self) -> dict:
        return {'creationDate': self.creationDate, 'reflectanceCubes': [i.toDict() for i in self.cubes]}


class ERIndexCube:
    def __init__(self, fileName: str, description: str, idTag: str, name: str, md5: str):
        self.fileName = fileName
        self.description = description
        self.idTag = idTag
        self.name = name
        self.md5 = md5

    @classmethod
    def fromDict(cls, d: dict) -> ERIndexCube:
        return cls(**d)

class ERDataDirectory:
    def __init__(self, directory: str):
        self._directory = directory
        self.index = ERIndex(os.path.join(self._directory, 'index.json'))
        files = glob(os.path.join(self._directory, f'*{ERMetadata.FILESUFFIX}'))
        files = [(f, ERMetadata.validPath(f)) for f in files]  # validPath returns True/False in awhether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        self.files = [ERMetadata.fromHdfFile(directory, name) for directory, name in files]
        calculatedIndex = self.buildIndexFromFiles()
        for i in self.index.cubes:
            i['downloaded'] = i.idTag in [cube.idTag for cube in calculatedIndex.cubes] #Replace this with code to indicate either `matches`, `md5` conflict, 'not indexed', or 'missing`

    def buildIndexFromFiles(self) -> ERIndex:
        """Scan the data files in the directory and construct and ERIndex from the metadata. The `description` field is left blank though."""
        cubes = []
        for erCube in self.files:
            md5hash = hashlib.md5()
            with open(erCube.filePath, 'rb') as f:
                md5hash.update(f.read())
            md5 = md5hash.hexdigest()  # The md5 checksum as a string of hex.
            cubes.append(ERIndexCube(erCube.filePath, '', erCube.idTag, erCube.directory2dirName(erCube.filePath)[-1], md5))
            return ERIndex(cubes)

if __name__ == '__main__':
    m = ERManager(applicationVars.extraReflectionDirectory)
