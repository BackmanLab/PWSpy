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

import json
import logging
import traceback
from typing import Optional

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QModelIndex, QPoint
from PyQt5.QtWidgets import QDialog, QWidget, QHBoxLayout, QPushButton, QAbstractItemView, QTableView, QVBoxLayout, \
    QMenu, QAction, QMessageBox
import pandas as pd
import typing
import numpy as np

from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndex
from pwspy.apps.sharedWidgets.extraReflectionManager._ERDataDirectory import ERDataDirectory
from pwspy.apps.sharedWidgets.extraReflectionManager.ERDataComparator import ERDataComparator
from pwspy.dataTypes import ExtraReflectanceCube
from mpl_qt_viz.visualizers import PlotNd


if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager


class ERUploaderWindow(QDialog):
    """This window provides the user a visual picture of the local and online status of the Extra Reflectance calibration file repository. It also allows uploading
    of files that are present locally but not on the server. It does not have good handling of edge cases, e.g. online server in inconsistent state."""
    def __init__(self, manager: ERManager, parent: Optional[QWidget] = None):
        self._manager = manager
        self._selectedId: str = None
        super().__init__(parent)
        self.setModal(False)
        self.setWindowTitle("Extra Reflectance File Manager")
        self.setLayout(QVBoxLayout())
        self.table = QTableView(self)
        self.fileStatus = self._manager.dataComparator.compare()
        self.table.setModel(PandasModel(self.fileStatus))
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.customContextMenuRequested.connect(self.openContextMenu)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.uploadButton = QPushButton("Upload to Drive")
        self.uploadButton.released.connect(self._updateGDrive)
        self.uploadButton.setToolTip("Upload any files for which the status is `Local Only` to the google drive account.")
        self.refreshButton = QPushButton('Refresh')
        self.refreshButton.setToolTip("Rescan the files in the applications data directory.")
        self.refreshButton.released.connect(self.refresh)
        self.updateIndexButton = QPushButton("Update Index File")
        self.updateIndexButton.setToolTip("Download the online index file and merge it with our local index file.")
        self.updateIndexButton.released.connect(self._updateIndexFile)
        self.layout().addWidget(self.table)
        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.uploadButton)
        l.addWidget(self.updateIndexButton)
        l.addWidget(self.refreshButton)
        w = QWidget()
        w.setLayout(l)
        self.layout().addWidget(w)
        self.table.setColumnWidth(0, 300); self.table.setColumnWidth(1, 150); self.table.setColumnWidth(2, 150)
        self.table.setMinimumWidth(sum(self.table.columnWidth(i)for i in range(self.table.model().columnCount())) + self.table.verticalHeader().width() + 20)

    def displayInfo(self, index: QModelIndex):
        msg = QMessageBox.information(self, 'Info', repr(self.fileStatus.iloc[index.row()]))

    def plotData(self, index: QModelIndex):
        idTag = self.fileStatus.iloc[index.row()]['idTag']
        md = self._manager.getMetadataFromId(idTag)
        erCube = ExtraReflectanceCube.fromMetadata(md)
        self.plotHandle = PlotNd(erCube.data)

    def openContextMenu(self, pos: QPoint):
        """This method opens a context menu, it should be called when the user right clicks."""
        index = self.table.indexAt(pos)
        row = self.fileStatus.iloc[index.row()]
        menu = QMenu()
        displayAction = QAction("Display Info")
        displayAction.triggered.connect(lambda: self.displayInfo(index))
        menu.addAction(displayAction)
        if row['Local Status'] == self._manager.dataComparator.local.DataStatus.found.value:
            plotAction = QAction("Plot Local Data")
            plotAction.triggered.connect(lambda: self.plotData(index))
            menu.addAction(plotAction)
        menu.exec(self.mapToGlobal(pos))

    def _updateGDrive(self):
        """Checks for all files taht are present locally but not on the server. Uploads those file and then overwrites the index."""
        try:
            status = self.fileStatus
            if not np.all((status['Index Comparison'] == ERDataComparator.ComparisonStatus.LocalOnly.value) | (status['Index Comparison'] == ERDataComparator.ComparisonStatus.Match.value)):
                raise ValueError("Uploading cannot be performed if the local index file is not valid. Try updating the index file.")
            uploadableRows = (status['Index Comparison'] == ERDataComparator.ComparisonStatus.LocalOnly.value) | (status['Online Status'] == ERDataDirectory.DataStatus.missing.value)
            if np.any(uploadableRows):  # There is something to upload
                for i, row, in status.loc[uploadableRows].iterrows():
                    fileName = [i.fileName for i in self._manager.dataComparator.local.index.cubes if i.idTag == row['idTag']][0]
                    self._manager.upload(fileName)
                self._manager.upload('index.json')
            self.refresh()
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.exception(e)
            mess = QMessageBox.information(self, 'Sorry', str(e))

    def refresh(self):
        """Scans local and online files to refresh the display."""
        self._manager.dataComparator.updateIndexes()
        self.fileStatus = self._manager.dataComparator.compare()
        self.table.setModel(PandasModel(self.fileStatus))

    def _updateIndexFile(self):
        self._manager.dataComparator.online.updateIndex()
        index = ERIndex.merge(self._manager.dataComparator.local.index, self._manager.dataComparator.online.index)
        self._manager.dataComparator.local.saveNewIndex(index)
        self.refresh()


class PandasModel(QtCore.QAbstractTableModel):
    """This Qt model is used to adapt a Pandas dataframe to a QTableView widget. This was found somewhere on stack overflow."""
    def __init__(self, df=pd.DataFrame(), parent=None):
        """`df` should be the dataframe that you want to view."""
        QtCore.QAbstractTableModel.__init__(self, parent=parent)
        self._df = df

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        if orientation == QtCore.Qt.Horizontal:
            try:
                return self._df.columns.tolist()[section]
            except (IndexError, ):
                return QtCore.QVariant()
        elif orientation == QtCore.Qt.Vertical:
            try:
                # return self.df.index.tolist()
                return self._df.index.tolist()[section]
            except (IndexError, ):
                return QtCore.QVariant()

    def _calculateColor(self, index: QModelIndex):
        if self._df.columns[index.column()] == 'idTag':
            c = QtGui.QColor('white')
        elif (self._df.iloc[index.row(), index.column()] == ERDataDirectory.DataStatus.found.value) or (self._df.iloc[index.row(), index.column()] == ERDataComparator.ComparisonStatus.Match.value):
            c = QtGui.QColor('green')
        else:
            c = QtGui.QColor('red')
        return c

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.BackgroundRole:
            color = self._calculateColor(index)
            return QtGui.QBrush(color)
        elif role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()

        if not index.isValid():
            return QtCore.QVariant()

        return QtCore.QVariant(str(self._df.iloc[index.row(), index.column()]))

    def setData(self, index, value, role):
        row = self._df.index[index.row()]
        col = self._df.columns[index.column()]
        if hasattr(value, 'toPyObject'):
            # PyQt4 gets a QVariant
            value = value.toPyObject()
        else:
            # PySide gets an unicode
            dtype = self._df[col].dtype
            if dtype != object:
                value = None if value == '' else dtype.type(value)
        self._df.set_value(row, col, value)
        return True

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QtCore.QModelIndex()):
        return len(self._df.columns)

    def sort(self, column, order):
        colname = self._df.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self._df.sort_values(colname, ascending= order == QtCore.Qt.AscendingOrder, inplace=True)
        self._df.reset_index(inplace=True, drop=True)
        self.layoutChanged.emit()