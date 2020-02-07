from __future__ import annotations

from typing import Optional

import pandas
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager, ERDownloader
from pwspy.apps.sharedWidgets.extraReflectionManager.ERDataDirectory import ERDataDirectory, EROnlineDirectory
from enum import Enum


class ERDataComparator:
    """A class to compare the local directory to the online directory.
    Args:
        downloader (Optional[ERDownloader]): Handles communication with GoogleDrive, if operating in offline mode this should be None
        directory (str): The file path where the files are stored locally.
    """

    class ComparisonStatus(Enum):
        LocalOnly = "Local Only"
        OnlineOnly = "Online Only"
        Md5Mismatch = 'MD5 Mismatch'
        Match = "Match"  # This is what we hope to see.

    def __init__(self, downloader: Optional[ERDownloader], directory: str):
        self.local: ERDataDirectory = ERDataDirectory(directory)
        self.online: Optional[EROnlineDirectory] = None if downloader is None else EROnlineDirectory(downloader)

    def updateIndexes(self):
        self.local.updateIndex()
        if self.online is not None:
            self.online.updateIndex()

    def compare(self) -> pandas.DataFrame:
        """Scans local and online files to put together an idea of the status."""
        localStatus = self.local.updateStatusFromFiles()
        if self.online is not None:
            onlineStatus = self.online.updateStatusFromFiles()
            status = pandas.merge(localStatus, onlineStatus, how='outer', on='idTag')
            status['Index Comparison'] = status.apply(lambda row: self._dataFrameCompare(row), axis=1)
            status = status[['idTag', 'Local Status', 'Online Status', 'Index Comparison']]  # Set the column order
        else:
            status = localStatus
            status['Index Comparison'] = self.ComparisonStatus.LocalOnly.value
            status = status[['idTag', 'Local Status', 'Index Comparison']]  # Set the column order
        return status

    def _dataFrameCompare(self, row) -> str:
        try:
            self.local.index.getItemFromIdTag(row['idTag'])
        except:
            return self.ComparisonStatus.OnlineOnly.value
        try:
            self.online.index.getItemFromIdTag(row['idTag'])
        except:
            return self.ComparisonStatus.LocalOnly.value
        if self.local.index.getItemFromIdTag(row['idTag']).md5 != self.online.index.getItemFromIdTag(row['idTag']).md5:
            return self.ComparisonStatus.Md5Mismatch.value
        else:
            return self.ComparisonStatus.Match.value
