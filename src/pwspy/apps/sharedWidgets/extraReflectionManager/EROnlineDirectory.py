from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
from pwspy.imCube import ExtraReflectanceCube
from pwspy.imCube.ExtraReflectanceCubeClass import ERMetadata
from pwspy.utility import GoogleDriveDownloader
import os
import tempfile
from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndex, ERIndexCube
import pandas as pd


class EROnlineDirectory:
    def __init__(self, manager: ERManager):
        self._manager = manager
        self.index: ERIndex = None
        self.status: pd.DataFrame = None
        self.rescan()

    def rescan(self):
        self.index = self.getIndexFile()
        self.status = #TODO finish


    def getIndexFile(self) -> ERIndex:
        """Return an ERIndex object from the 'index.json' file saved on Google Drive."""
        tempDir = tempfile.mkdtemp()
        # if not os.path.exists(tempDir):
        #     os.mkdir(tempDir)
        indexDir = os.path.join(tempDir, 'index.json')
        if os.path.exists(indexDir):
            os.remove(indexDir)
        self._manager.download('index.json', tempDir)
        index = ERIndex.loadFromFile(indexDir)
        os.remove(indexDir)
        os.rmdir(tempDir)
        return index

    def buildIndexFromOnlineFiles(self) -> ERIndex:
        """Return an ERIndex object from the HDF5 data files saved on Google Drive. No downloading required, just scanning metadata."""
        # api = self._manager._downloader.api
        downloader = self._manager._downloader
        files = downloader.getFolderIdContents(
            downloader.getIdByName('PWSAnalysisAppHostedFiles'))
        files = downloader.getFolderIdContents(
            downloader.getIdByName('ExtraReflectanceCubes', fileList=files))
        files = [f for f in files if ERMetadata.FILESUFFIX in f['name']]  # Select the dictionaries that correspond to a extra reflectance data file
        files = [ERIndexCube(fileName=f['name'], md5=f['md5Checksum'], name=ERMetadata.directory2dirName(f['name'])[-1], description=None, idTag=None) for f in files]
        return ERIndex(files)
