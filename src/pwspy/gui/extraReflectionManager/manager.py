import json
import os
from glob import glob
import jsonschema
from PyQt5.QtCore import QObject

from pwspy import ExtraReflectanceCube


class ERManager(QObject):
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

        import pickle
        import os.path
        from googleapiclient.discovery import build
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request

        # If modifying these scopes, delete the file token.pickle.
        SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

        def main():
            """Shows basic usage of the Drive v3 API.
            Prints the names and ids of the first 10 files the user has access to.
            """
            creds = None
            # The file token.pickle stores the user's access and refresh tokens, and is
            # created automatically when the authorization flow completes for the first
            # time.
            if os.path.exists('token.pickle'):
                with open('token.pickle', 'rb') as token:
                    creds = pickle.load(token)
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', SCOPES)
                    creds = flow.run_local_server()
                # Save the credentials for the next run
                with open('token.pickle', 'wb') as token:
                    pickle.dump(creds, token)

            service = build('drive', 'v3', credentials=creds)

            # Call the Drive v3 API
            results = service.files().list(
                pageSize=10, fields="nextPageToken, files(id, name)").execute()
            items = results.get('files', [])

            if not items:
                print('No files found.')
            else:
                print('Files:')
                for item in items:
                    print(u'{0} ({1})'.format(item['name'], item['id']))

    def setAuth(self, username: str, password: str):
        self.auth = {'user': username, 'pw': password}