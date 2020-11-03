import typing

from PyQt5 import QtCore
from PyQt5.QtCore import QModelIndex
from .item import TreeItem


class TreeModel(QtCore.QAbstractItemModel):
    def __init__(self, root: TreeItem, parent=None):
        super(TreeModel, self).__init__(parent)
        self._rootItem = TreeItem()  # This will be invisible but will determine the header labels.
        self._rootItem.setData(0, "Steps")
        self._rootItem.addChild(root)

    def invisibleRootItem(self) -> TreeItem:
        return self._rootItem

    def columnCount(self, parent: QModelIndex) -> int:
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self._rootItem.columnCount()

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        if role != QtCore.Qt.DisplayRole:
            return None
        item: TreeItem = index.internalPointer()
        col = index.column()
        return item.data(col)

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def setData(self, index: QModelIndex, value: typing.Any, role: int = ...) -> bool:
        return True

    def headerData(self, section, orientation, role):
        if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return self._rootItem.data(section)
        return None

    def index(self, row: int, column: int, parent: QModelIndex):
        # if not self.hasIndex(row, column, parent): #This was causing bugs
        #     return QtCore.QModelIndex()
        if parent.isValid():
            parentItem = parent.internalPointer()
        else:
            parentItem = self._rootItem
        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        childItem = index.internalPointer()
        parentItem = childItem.parent()
        if parentItem == self._rootItem:
            return QtCore.QModelIndex()
        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent: QModelIndex):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            return self._rootItem.childCount()
        else:
            return parent.internalPointer().childCount()