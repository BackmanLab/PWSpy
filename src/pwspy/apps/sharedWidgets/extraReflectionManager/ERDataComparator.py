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
        self.local = ERDataDirectory(directory)
        self.online = None if downloader is None else EROnlineDirectory(downloader)
        self.status: pandas.DataFrame = None
        self.compare()

    def rescan(self):
        """Scans local and online files to put together an idea of the status. Do the data files match the
        index file? etc. It's really over complicated. Could use some work"""
        self.local.rescan()
        if self.online is not None:
            self.online.rescan()
        self.compare()

    def compare(self):
        if self.online is not None:
            self.status = pandas.merge(self.local.status, self.online.status, how='outer', on='idTag')
            self.status['Index Comparison'] = self.status.apply(lambda row: self._dataFrameCompare(row), axis=1)
            self.status = self.status[['idTag', 'Local Status', 'Online Status', 'Index Comparison']]  # Set the column order
        else:
            self.status = self.local.status
            self.status['Index Comparison'] = self.ComparisonStatus.LocalOnly.value
            self.status = self.status[['idTag', 'Local Status', 'Index Comparison']]  # Set the column order

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
