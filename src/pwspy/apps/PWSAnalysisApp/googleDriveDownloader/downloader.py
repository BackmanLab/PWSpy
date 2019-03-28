import os
import pickle
from typing import Optional, List

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload


class GoogleDriveDownloader:
    def __init__(self, authPath: str):
        """AuthPath is the folder to store authentication files."""
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
            with open(self.authPath, 'wb') as token: # Save the credentials for the next run
                pickle.dump(creds, token)

        self.api = build('drive', 'v3', credentials=creds) #this returns access to the drive api. see google documentation
        self.updateFilesList()

    def updateFilesList(self):
        results = self.api.files().list(fields="nextPageToken, files(id, name, parents)").execute()
        self.allFiles = results.get('files', [])

    def getIdByName(self, name: str, fileList: Optional = None) -> int:
        if fileList is None: fileList = self.allFiles
        return [i['id'] for i in fileList if i['name'] == name][0]

    def getFolderIdContents(self, id: int) -> List:
        files = [i for i in self.allFiles if 'parents' in i] # Get rid of parentless files. they will cause errors.
        return [i for i in files if id in i['parents']]

    def downloadFile(self, id: int, savePath: str):
        fileRequest = self.api.files().get_media(fileId=id)
        with open(savePath, 'wb') as f:
            downloader = MediaIoBaseDownload(f, fileRequest)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % int(status.progress() * 100))
