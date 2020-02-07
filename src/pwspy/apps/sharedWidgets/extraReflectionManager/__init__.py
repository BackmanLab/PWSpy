from __future__ import annotations
import os
from typing import Optional

import httplib2
from PyQt5 import QtCore
from PyQt5.QtCore import QObject, QThread
from PyQt5.QtWidgets import QMessageBox, QWidget
from googleapiclient.http import MediaIoBaseDownload

from pwspy.apps.sharedWidgets.dialogs import BusyDialog
from pwspy.apps.sharedWidgets.extraReflectionManager.ERDataComparator import ERDataComparator
from pwspy.apps.sharedWidgets.extraReflectionManager.ERDataDirectory import ERDataDirectory, EROnlineDirectory
from .ERSelectorWindow import ERSelectorWindow
from .ERUploaderWindow import ERUploaderWindow
from pwspy.dataTypes import ERMetadata
from pwspy.utility._GoogleDriveDownloader import GoogleDriveDownloader
from .exceptions import OfflineError
from pwspy.apps.PWSAnalysisApp import applicationVars
from google.auth.exceptions import TransportError


#TODO this whole submodule is kind of a fragile mess and probably not organized in a smart way.


def _offlineDecorator(func):
    """Functions decorated with this will raise an OfflineError if they are attempted to be called while the ERManager
    is in offline mode. Only works on instance methods."""
    def wrappedFunc(self, *args, **kwargs):
        if self.offlineMode:
            print("Warning: Attempting to download when ERManager is in offline mode.")
            raise OfflineError("Is Offline")
        func(self, *args, **kwargs)
    return wrappedFunc


class ERManager:
    """This class expects that the google drive application will already have access to a folder named
    `PWSAnalysisAppHostedFiles` which contains a folder `ExtraReflectanceCubes`, you will
    have to create these manually if starting on a new Drive account."""
    def __init__(self, filePath: str):
        self._directory = filePath
        self.offlineMode = False
        creds = _QtGoogleDriveDownloader.getCredentials(applicationVars.googleDriveAuthPath)
        if creds is None:  # Check if the google drive credentials exists and if they don't then give the user a message.
            msg = QMessageBox.information(None, "Time to log in!", "Please log in to the google drive account containing the PWS Calibration Database. This is currently backman.lab@gmail.com")
        try:
            self._downloader = ERDownloader(applicationVars.googleDriveAuthPath)
        except (TransportError, httplib2.ServerNotFoundError):
            self.offlineMode = True
            print("Google Drive connection failed. Proceeding in offline mode.")
            self._downloader: ERDownloader = None
        indexPath = os.path.join(self._directory, 'index.json')
        if not os.path.exists(indexPath):
            self.download('index.json')
        self.dataComparator = ERDataComparator(self._downloader, self._directory) #TODO circular reference!

    def createSelectorWindow(self, parent: QWidget):
        return ERSelectorWindow(self, parent)

    def createManagerWindow(self, parent: QWidget):
        return ERUploaderWindow(self, parent)

    def rescan(self):
        """Scans local and online files to put together an idea of the status. Do the data files match the
        index file? etc. It's really over complicated. Could use some work"""
        self.dataComparator.rescan()

    @_offlineDecorator
    def download(self, fileName: str, parentWidget: Optional[QWidget] = None):
        """Begin downloading `fileName` in a separate thread. Use the main thread to update a progress bar.
        If directory is left blank then file will be downloaded to the ERManager main directory"""
        self._downloader.download(fileName, self._directory, parentWidget)

    @_offlineDecorator
    def upload(self, fileName: str):
        """Uploads the file at `fileName` to the `ExtraReflectanceCubes` folder of the google drive account"""
        filePath = os.path.join(self._directory, fileName)
        self._downloader.upload(filePath)

    def getMetadataFromId(self, idTag: str) -> ERMetadata:
        """Given the unique idTag string for an ExtraReflectanceCube this will search the index.json and return the
        ERMetadata file. If it cannot be found then an `IndexError will be raised."""
        try:
            match = [item for item in self.dataComparator.local.index.cubes if item.idTag == idTag][0]
        except IndexError:
            raise IndexError(f"An ExtraReflectanceCube with idTag {idTag} was not found in the index.json file at {self._directory}.")
        return ERMetadata.fromHdfFile(self._directory, match.name)


class _QtGoogleDriveDownloader(GoogleDriveDownloader, QObject):
    """Same as the standard google drive downloader except it emits a progress signal after each chunk downloaded. This can be used to update a progress bar."""
    progress = QtCore.pyqtSignal(int) # gives an estimate of download progress percentage

    def __init__(self, authPath: str):
        GoogleDriveDownloader.__init__(self, authPath)
        QObject.__init__(self)

    def downloadFile(self, Id: int, savePath: str):
        """Save the file with googledrive file identifier `Id` to `savePath` while emitting the `progress` signal
        which can be connected to a progress bar or whatever."""
        fileRequest = self.api.files().get_media(fileId=Id)
        with open(savePath, 'wb') as f:
            downloader = MediaIoBaseDownload(f, fileRequest)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                self.progress.emit(int(status.progress() * 100))


class ERDownloader:
    """Implements downloading functionality specific to the structure that we have calibration files stored on our google drive account."""
    def __init__(self, authPath: str):
        self._downloader = _QtGoogleDriveDownloader(authPath)


    def download(self, fileName: str, directory: str, parentWidget: Optional[QWidget] = None):
        """Begin downloading `fileName` in a separate thread. Use the main thread to update a progress bar.
        If directory is left blank then file will be downloaded to the ERManager main directory"""
        if fileName not in [i['name'] for i in self._downloader.allFiles]:
            raise ValueError(f"File {fileName} does not exist on google drive")
        t = self._DownloadThread(self._downloader, fileName, directory)
        b = BusyDialog(parentWidget, f"Downloading {fileName}. Please Wait...", progressBar=True)  # This dialog blocks the screen until the download thread is completed.
        t.finished.connect(b.accept)  # When the thread finishes, close the busy dialog.
        self._downloader.progress.connect(b.setProgress)  # Progress from the downloader updates a progress bar on the busy dialog.
        t.errorOccurred.connect(lambda e: QMessageBox.information(parentWidget, 'Error in Drive Downloader Thread', str(e)))
        t.start()
        b.exec()

    def upload(self, filePath: str):
        parentId = self._downloader.getIdByName("ExtraReflectanceCubes")
        self._downloader.uploadFile(filePath, parentId)

    class _DownloadThread(QThread):
        """A QThread to download from google drive"""
        errorOccurred = QtCore.pyqtSignal(
            Exception)  # If an exception occurs it can be passed to another thread with this signal

        def __init__(self, downloader: GoogleDriveDownloader, fileName: str, directory: str):
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


