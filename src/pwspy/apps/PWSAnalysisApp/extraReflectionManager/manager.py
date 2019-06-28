import json
import os
from glob import glob
import jsonschema
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QThread
from PyQt5.QtWidgets import QMessageBox, QApplication
from googleapiclient.http import MediaIoBaseDownload

from pwspy.apps.PWSAnalysisApp.sharedWidgets.dialogs import BusyDialog
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from pwspy.utility.GoogleDriveDownloader import GoogleDriveDownloader

from pwspy.imCube import ExtraReflectanceCube
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
        """Begin downloading `fileName` in a separate thread. Use the main thread to update a progress bar"""
        class DownloadThread(QThread):
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

        if self.downloader is None:
            self.downloader = QtGoogleDriveDownloader(applicationVars.googleDriveAuthPath)
        t = DownloadThread(self.downloader, fileName, self.directory)
        b = BusyDialog(QApplication.instance().window, f"Downloading {fileName}. Please Wait...", progressBar=True)
        t.finished.connect(b.accept)
        self.downloader.progress.connect(b.setProgress)
        t.errorOccurred.connect(lambda e: QMessageBox.information(QApplication.instance().window, 'Uh Oh', str(e)))
        t.start()
        b.exec()


    def getMetadataFromId(self, Id: str) -> ERMetadata:
        """Given the Id string for ExtraReflectanceCube this will search the index.json and return the ERMetadata file"""
        try:
            match = [item for item in self.index['reflectanceCubes'] if item['idTag'] == Id][0]
        except IndexError:
            raise IndexError(f"An ExtraReflectanceCube with idTag {Id} was not found in the index.json file at {self.directory}.")
        return ERMetadata.fromHdfFile(self.directory, match['name'])


class QtGoogleDriveDownloader(GoogleDriveDownloader, QObject):
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

if __name__ == '__main__':
    m = ERManager(applicationVars.extraReflectionDirectory)
