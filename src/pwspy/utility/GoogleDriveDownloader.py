import os
import pickle
from typing import Optional, List

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload


class GoogleDriveDownloader:
    def __init__(self, authPath: str):
        """AuthPath is the folder to store authentication files. Before this class will work you will need to place
        `credentials.json` in the authPath. You can get this file from the online Google Drive api console.
        Upon initializing an instance of this class you will be asked for username and password if you don't already have
        authentication saved from a previous login."""
        self.authPath = authPath
        tokenPath = os.path.join(self.authPath, 'driveToken.pickle')
        credPath = os.path.join(self.authPath, 'credentials.json')
        creds = None
        if os.path.exists(tokenPath):
            with open(tokenPath, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credPath, ['https://www.googleapis.com/auth/drive.readonly'])
                creds = flow.run_local_server()
            with open(tokenPath, 'wb') as token: # Save the credentials for the next run
                pickle.dump(creds, token)

        self.api = build('drive', 'v3', credentials=creds) #this returns access to the drive api. see google documentation
        self.updateFilesList()

    def updateFilesList(self):
        """Update the list of all files in the google drive account. This is automatically called during initialization."""
        results = self.api.files().list(fields="nextPageToken, files(id, name, parents)").execute()
        self.allFiles = results.get('files', [])

    def getIdByName(self, name: str, fileList: Optional = None) -> int:
        """Return the file id associated with a filename. fileList can be a collection of metadata such as is returned by
        getFolderIDContents. If left blank then all files of the google drive account will be searched. If there are multiple
        files with the same name the first match that is found will be returned."""
        if fileList is None: fileList = self.allFiles
        return [i['id'] for i in fileList if i['name'] == name][0]

    def getFolderIdContents(self, id: int) -> List:
        """Return the api metadata for all files contained within the folder associated with `id`."""
        files = [i for i in self.allFiles if 'parents' in i] # Get rid of parentless files. they will cause errors.
        return [i for i in files if id in i['parents']]

    def downloadFile(self, id: int, savePath: str):
        """Save the file with `id` to `savePath`"""
        fileRequest = self.api.files().get_media(fileId=id)
        with open(savePath, 'wb') as f:
            downloader = MediaIoBaseDownload(f, fileRequest)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % int(status.progress() * 100))
