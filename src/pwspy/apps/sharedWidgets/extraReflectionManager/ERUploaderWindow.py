from __future__ import annotations
from typing import Optional

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QModelIndex, QPoint
from PyQt5.QtWidgets import QDialog, QWidget, QHBoxLayout, QPushButton, QAbstractItemView, QTableView, QVBoxLayout, \
    QMenu, QAction, QMessageBox
import pandas as pd
import typing
import os

from pwspy.apps.sharedWidgets.extraReflectionManager.ERDataDirectory import ERDataDirectory

if typing.TYPE_CHECKING:
    from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager


class ERUploaderWindow(QDialog):
    def __init__(self, manager: ERManager, parent: Optional[QWidget] = None):
        self._manager = manager
        self._selectedId: str = None
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Extra Reflectance File Manager")
        self.setLayout(QVBoxLayout())
        self.table = QTableView(self)
        self.table.setModel(PandasModel(self._manager.dataDir.status))
        # self.table.doubleClicked.connect(self.displayInfo)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.customContextMenuRequested.connect(self.openContextMenu)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.uploadButton = QPushButton("Upload to Drive")
        self.uploadButton.released.connect(self._updateGDrive)
        self.refreshButton = QPushButton('Refresh')
        self.refreshButton.setToolTip("Rescan the files in the applications data directory.")
        self.refreshButton.released.connect(self.refresh)
        self.layout().addWidget(self.table)
        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.uploadButton)
        l.addWidget(self.refreshButton)
        w = QWidget()
        w.setLayout(l)
        self.layout().addWidget(w)
        self.table.setColumnWidth(0, 300); self.table.setColumnWidth(1, 150); self.table.setColumnWidth(2, 150)
        self.table.setMinimumWidth(sum(self.table.columnWidth(i)for i in range(self.table.model().columnCount())) + self.table.verticalHeader().width() + 20)

    def displayInfo(self, index: QModelIndex):
        msg = QMessageBox(self, 'Info', repr(self._manager.dataDir.status.iloc[index.row()]))

    def openContextMenu(self, pos: QPoint):
        index = self.table.indexAt(pos)
        row = self._manager.dataDir.status.iloc[index.row()]
        menu = QMenu()
        displayAction = QAction("Display Info")
        displayAction.triggered.connect(lambda: self.displayInfo(index))
        menu.addAction(displayAction)
        menu.exec(self.mapToGlobal(pos))

    def _updateGDrive(self):
        mess = QMessageBox.information(self, 'Sorry', "This function is not yet implemented")

    def refresh(self):
        self._manager.dataDir.rescan()
        self.table.setModel(PandasModel(self._manager.dataDir.status))


class PandasModel(QtCore.QAbstractTableModel):
    def __init__(self, df=pd.DataFrame(), parent=None):
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
        if self._df.columns[index.column()] != 'status':
            c = QtGui.QColor('white')
        elif self._df.iloc[index.row(), index.column()] == ERDataDirectory.DataStatus.found.value:
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

        return QtCore.QVariant(str(self._df.ix[index.row(), index.column()]))

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