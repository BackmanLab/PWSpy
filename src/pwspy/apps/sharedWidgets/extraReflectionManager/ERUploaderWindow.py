from __future__ import annotations
from typing import Optional

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QModelIndex, QPoint
from PyQt5.QtWidgets import QDialog, QWidget, QHBoxLayout, QPushButton, QAbstractItemView, QTableView, QVBoxLayout, \
    QMenu, QAction
import pandas as pd
import typing

from pwspy.apps.sharedWidgets.extraReflectionManager.ERDataDirectory import DataStatus

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
        # self.table.verticalHeader().hide()
        # self.table.horizontalHeader().setStretchLastSection(True)
        # self.table.itemDoubleClicked.connect(self.displayInfo)
        # self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        # self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        # self.table.setRowCount(0)
        # self.table.setColumnCount(3)
        # self.table.setSortingEnabled(True)
        # self.table.setHorizontalHeaderLabels([" ", "System", "Date"])
        # self.table.setColumnWidth(0, 10)

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
        self.table.setColumnWidth(0, 300); self.table.setColumnWidth(1, 150)
        self.table.setMinimumWidth(sum(self.table.columnWidth(i)for i in range(self.table.model().columnCount())) + self.table.verticalHeader().width() + 20)

    def displayInfo(self, index: QModelIndex):
        print(self._manager.dataDir.status.iloc[index.row()])

    def updateMD5FromData(self):
        pass

    def openContextMenu(self, pos: QPoint):
        index = self.table.indexAt(pos)
        row = self._manager.dataDir.status.iloc[index.row()]
        menu = QMenu()
        displayAction = QAction("Display Info")
        displayAction.triggered.connect(lambda: self.displayInfo(index))
        menu.addAction(displayAction)
        if row['status'] == DataStatus.md5Confict.value:
            correctAction = QAction("Update indexed md5")
            correctAction.triggered.connect(self.updateMD5FromData)
            menu.addAction(correctAction)
        menu.exec(self.mapToGlobal(pos))

    def _updateGDrive(self):
        pass


    def refresh(self):
        self._manager.dataDir.rescan()
        self.table.setModel(PandasModel(self._manager.dataDir.status))


class PandasModel(QtCore.QAbstractTableModel):
    def __init__(self, df = pd.DataFrame(), parent=None):
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

    def _calculateColorForRow(self, row: int):
        if self._df.iloc[row]['status'] == 'Found':
            c = QtGui.QColor('green')
        else:
            c = QtGui.QColor('red')
        return c

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.BackgroundRole:
            color = self._calculateColorForRow(index.row())
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