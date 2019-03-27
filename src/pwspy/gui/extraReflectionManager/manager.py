import json
import os
from glob import glob
import jsonschema
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from googleapiclient.http import MediaIoBaseDownload

from pwspy import ExtraReflectanceCube
from pwspy.gui import applicationVars


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
                       'name': {'type': 'string'}
                   },
                   'required': ['fileName', 'description', 'idTag', 'name']
               }

            }
       }
    }
    authPath = os.path.join(applicationVars.extraReflectionDirectory, 'driveToken.pickle')

    def __init__(self, filePath: str):
        self.directory = filePath
        self.auth = None
        self._initialize()

    def _initialize(self):
        indexPath = os.path.join(self.directory, 'index.json')
        if not os.path.exists(indexPath):
            self.download('index.json')
        with open(indexPath, 'r') as f:
            self.index = json.load(f)
        jsonschema.validate(self.index, schema=self._indexSchema)
        files = glob(os.path.join(self.directory, f'*{ExtraReflectanceCube.fileSuffix}'))
        files = [(f, ExtraReflectanceCube.validPath(f)) for f in files]  # validPath returns whether the datacube was found.
        files = [(directory, name) for f, (valid, directory, name) in files if valid]
        tags = [ExtraReflectanceCube.getMetadata(directory, name)['idTag'] for directory, name in files]
        for i in self.index['reflectanceCubes']:
            i['downloaded'] = i['idTag'] in tags

    def download(self, fileName: str):
        """Shows basic usage of the Drive v3 API.
        Prints the names and ids of the first 10 files the user has access to.
        """
        creds = None
        if os.path.exists(self.authPath):
            with open(self.authPath, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', ['https://www.googleapis.com/auth/drive.readonly'])
                creds = flow.run_local_server()
            with open(self.authPath, 'wb') as token: # Save the credentials for the next run
                pickle.dump(creds, token)

        drive = build('drive', 'v3', credentials=creds) #this returns access to the drive api. see google documentation

        # Call the Drive v3 API
        results = drive.files().list(fields="nextPageToken, files(id, name, parents)").execute()
        items = results.get('files', [])
        mainFolderId = [item['id'] for item in items if item['name'] == 'PWSAnalysisAppHostedFiles'][0]
        items = [item for item in items if 'parents' in item] #Any parentless files are just going to cause errors on the next line.
        erFolderId = [item['id'] for item in items if (mainFolderId in item['parents']) and (item['name'] == 'ExtraReflectanceCubes')][0]
        erItems = [item for item in items if erFolderId in item['parents']] #Now we have only the files under the extraReflectance Folder
        fileId = [item['id'] for item in erItems if item['name'] == fileName][0]
        fileRequest = drive.files().get_media(fileId=fileId)
        with open(os.path.join(self.directory, fileName), 'wb') as f:
            downloader = MediaIoBaseDownload(f, fileRequest)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print("Download %d%%." % int(status.progress() * 100))

if __name__ == '__main__':
    m = ERManager(applicationVars.extraReflectionDirectory)
    m.download('index.json')