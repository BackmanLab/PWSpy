import os
import pickle
from io import IOBase
from typing import Optional, List, Dict

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload


class GoogleDriveDownloader:
    def __init__(self, authPath: str):
        """AuthPath is the folder to store authentication files. Before this class will work you will need to place
        `credentials.json` in the authPath. You can get this file from the online Google Drive api console. Create an Oauth 2.0 credential with access to the drive.file api.
        Upon initializing an instance of this class you will be asked for username and password if you don't already have
        authentication saved from a previous login."""
        self._allFiles = None
        self.authPath = authPath
        tokenPath = os.path.join(self.authPath, 'driveToken.pickle')
        credPath = os.path.join(self.authPath, 'credentials.json')
        creds = self.getCredentials(self.authPath)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credPath, ['https://www.googleapis.com/auth/drive.file'])
                creds = flow.run_local_server(port=8090)
            with open(tokenPath, 'wb') as token:  # Save the credentials for the next run
                pickle.dump(creds, token)
        self.api = build('drive', 'v3', credentials=creds) #this returns access to the drive api. see google documentation
        self._updateFilesList()

    @staticmethod
    def getCredentials(authPath: str):
        tokenPath = os.path.join(authPath, 'driveToken.pickle')
        creds = None
        if os.path.exists(tokenPath):
            with open(tokenPath, 'rb') as token:
                creds = pickle.load(token)
        return creds

    def _updateFilesList(self):
        """Update the list of all files in the google drive account. This is automatically called during initialization and after uploading a new file.
        I don't think it should be needed anywhere else."""
        results = self.api.files().list(fields="nextPageToken, files(id, name, parents, md5Checksum)").execute()
        self._allFiles = results.get('files', [])

    def getIdByName(self, name: str, fileList: Optional = None) -> str:
        """Return the file id associated with a filename. fileList can be a collection of metadata such as is returned by
        getFolderIDContents. If left blank then all files of the google drive account will be searched. If there are multiple
        files with the same name the first match that is found will be returned."""
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
        """Return the api metadata for all files contained within the folder associated with `id`."""
        files = [i for i in self._allFiles if 'parents' in i] # Get rid of parentless files. they will cause errors.
        return [i for i in files if Id in i['parents']]

    def downloadFile(self, Id: str, file: IOBase):
        """Save the file with `id` to `savePath`"""
        fileRequest = self.api.files().get_media(fileId=Id)
        downloader = MediaIoBaseDownload(file, fileRequest)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            print("Download %d%%." % int(status.progress() * 100))

    def createFolder(self, name: str, parentId: Optional[str] = None) -> str:
        """Creates a folder with name `name` and returns the id number of the folder
        If parentId is provided then the folder will be created inside the parent folder"""
        folderMetadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
        if parentId: folderMetadata['parents'] = [parentId]
        folder = self.api.files().create(body=folderMetadata, fields='id').execute()
        return folder.get('id')

    def uploadFile(self, filePath: str, parentId: str) -> str:
        """upload the file at `filePath` to the folder with `parentId`. keeping the original file name.
        Return the new file's id. If a file with the same parent and name already exists, replace it."""
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
        file = self.api.files().get(fileId=fileId, fields='parents').execute()
        oldParents = ','.join(file.get('parents'))
        file = self.api.files().update(fileId=fileId, addParents=newFolderId, removeParents=oldParents, fields='id, parents').execute()


if __name__ == '__main__':
    g = GoogleDriveDownloader(r'C:\Users\backman05\PwspyApps\PWSAnalysisData\GoogleDrive')
