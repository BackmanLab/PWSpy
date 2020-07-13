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

import logging
import os
import pickle
from io import IOBase
from typing import Optional, List, Dict

import logging
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
import typing
if typing.TYPE_CHECKING:
    from google.oauth2.credentials import Credentials



class GoogleDriveDownloader:
    """Handles downloading and uploading files from Google Drive.

    Upon initializing an instance of this class you will be asked for username and password if you don't already have
    authentication saved from a previous login.

    Args:
        authPath: The folder to store authentication files. Before this class will work you will need to place
            `credentials.json` in the authPath. You can get this file from the online Google Drive api console. Create
            an Oauth 2.0 credential with access to the `drive.file` api.

."""
    def __init__(self, authPath: str):
        self._allFiles = None  #A list of all the files that we have access to. updated by self._updateFilesList()
        self._authPath = authPath
        tokenPath = os.path.join(self._authPath, 'driveToken.pickle')
        credPath = os.path.join(self._authPath, 'credentials.json')
        creds = self.getCredentials(self._authPath)
        if not creds or not creds.valid:  # If there are no (valid) credentials available, let the user log in.
            if creds and creds.expired and creds.refresh_token:  # Attempt to refresh the credentials.
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credPath, ['https://www.googleapis.com/auth/drive.file'])
                creds = flow.run_local_server(port=8090)  # Opens the google login window in a browser.
            with open(tokenPath, 'wb') as token:  # Save the credentials for the next run
                pickle.dump(creds, token)
        self.api = build('drive', 'v3', credentials=creds)  # this returns access to the drive api. see google documentation. All drive related functionality happens through this api.
        self._updateFilesList()

    @staticmethod
    def getCredentials(authPath: str) -> Credentials:
        """
        Args:
            authPath: The folder path to the authentication folder.

        Returns:
             The Google Drive credentials stored in `driveToken.pickle`
        """
        tokenPath = os.path.join(authPath, 'driveToken.pickle')
        creds = None
        if os.path.exists(tokenPath):
            with open(tokenPath, 'rb') as token:
                creds = pickle.load(token)
        return creds

    def _updateFilesList(self):
        """Update the list of all files in the Google Drive account. This is automatically called during initialization
         and after uploading a new file. I don't think it should be needed anywhere else."""
        results = self.api.files().list(fields="nextPageToken, files(id, name, parents, md5Checksum)").execute()
        self._allFiles = results.get('files', [])

    def getIdByName(self, name: str, fileList: Optional[List] = None) -> str:
        """Return the file id associated with a filename.

        Args:
            name: The filename you want the ID for.
            fileList: A list of metadata such as is returned by getFolderIDContents. if left as `None` then all files
            are searched. If there are multiple files with the same name the first match that is found will be returned.

        Returns:
            The ID string of the file.
        """
        if fileList is None:
            fileList = self._allFiles
        matches = [i['id'] for i in fileList if i['name'] == name]
        if len(matches) > 1:
            raise ValueError(f"Google Drive found multiple files matching file name: {name}")
        elif len(matches) == 0:
            raise ValueError(f"Google Drive found not files matching file name: {name}")
        else:
            return matches[0]

    def getFolderIdContents(self, Id: str) -> List[Dict]:
        """Return the API metadata for all files contained within the folder associated with `id`.

        Args:
            Id: the file ID as returned by `getIdByName`.

        Returns:
            A list of file metadata.
        """
        files = [i for i in self._allFiles if 'parents' in i] # Get rid of parentless files. they will cause errors.
        return [i for i in files if Id in i['parents']]

    def downloadFile(self, Id: str, file: IOBase):
        """Save the file with `id` as it Google Drive ID

        Args:
            Id: the file ID as returned by `getIdByName`.
            file: A file or other stream to save to.
        """
        fileRequest = self.api.files().get_media(fileId=Id)
        downloader = MediaIoBaseDownload(file, fileRequest)
        done = False
        logger = logging.getLogger(__name__)
        while done is False:
            status, done = downloader.next_chunk()
            logger.info("Download %d%%." % int(status.progress() * 100))

    def createFolder(self, name: str, parentId: Optional[str] = None) -> str:
        """Creates a folder with name `name` and returns the id number of the folder
        If parentId is provided then the folder will be created inside the parent folder.

        Args:
            name: The name of the new folder
            parentId: The ID of the folder you want to create this folder inside of.

        Returns:
            The ID of the new folder
        """
        folderMetadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parentId: folderMetadata['parents'] = [parentId]
        folder = self.api.files().create(body=folderMetadata, fields='id').execute()
        return folder.get('id')

    def uploadFile(self, filePath: str, parentId: str) -> str:
        """Upload the file at `filePath` to the folder with `parentId`, keeping the original file name.
        If a file with the same parent and name already exists, replace it.

        Args:
            filePath: the local path the file that should be uploaded
            parentId: The ID of the folder that the file should be uploaded to.

        Returns:
            The ID of the newly uploaded file.

        """
        fileName = os.path.split(filePath)[-1]
        existingFiles = self.getFolderIdContents(parentId)
        if fileName in [i['name'] for i in existingFiles]: #FileName already exists
            existingId = [i['id'] for i in existingFiles if i['name'] == fileName][0]
            self.api.files().delete(fileId=existingId).execute()
        fileMetadata = {'name': fileName, 'parents': [parentId]}
        media = MediaFileUpload(filePath)
        file = self.api.files().create(body=fileMetadata, media_body=media, fields='id').execute()
        self._updateFilesList()
        return file.get('id')

    def moveFile(self, fileId: str, newFolderId: str):
        """Move a file that is already uploaded to Google Drive.

        Args:
            fileId: the ID of the file that should be moved.
            newFolderId: The ID of the parent folder you want to move the file to.

        """
        file = self.api.files().get(fileId=fileId, fields='parents').execute()
        oldParents = ','.join(file.get('parents'))
        file = self.api.files().update(fileId=fileId, addParents=newFolderId, removeParents=oldParents, fields='id, parents').execute()


if __name__ == '__main__':
    g = GoogleDriveDownloader(r'C:\Users\backman05\PwspyApps\PWSAnalysisData\GoogleDrive')
