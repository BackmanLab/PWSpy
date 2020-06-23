from __future__ import annotations

import typing
from io import UnsupportedOperation


class TreeItem:
    """Basic implementation of an item for a tree. Our treemodel is designed to work with this class and it's subclasses."""
    def __init__(self):
        self._parentItem = None
        self._itemData = {}
        self._childItems: typing.List[TreeItem] = []

    def addChild(self, item: TreeItem):
        item._parentItem = self
        self._childItems.append(item)


    def addChildren(self, children: typing.Sequence[TreeItem]):
        for i in children:
            i._parentItem = self
        self._childItems.extend(children)

    def child(self, row) -> TreeItem:
        return self._childItems[row]

    def children(self) -> typing.Tuple[TreeItem]:
        return tuple(self._childItems)

    def childCount(self) -> int:
        return len(self._childItems)

    def columnCount(self) -> int:
        """The treemodel is designed to create one column for each element in itemData"""
        return len(self._itemData)

    def data(self, column: int) -> typing.Any:
        try:
            return self._itemData[column]
        except KeyError:
            return None

    def setData(self, column: int, data: typing.Any):
        self._itemData[column] = data

    def parent(self) -> TreeItem:
        return self._parentItem

    def row(self) -> int:
        """Return which row we are with respect to the parent."""
        if self._parentItem:
            return self._parentItem._childItems.index(self)
        else:
            return None


class SelfTreeItem(TreeItem):
    """A tree item which returns itself as as its `data`"""
    def columnCount(self): return 1
    def data(self, column): return self
    def setData(self, column, data): raise UnsupportedOperation()
