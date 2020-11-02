from __future__ import annotations
import typing
from PyQt5 import QtCore


class TreeItem:
    """Basic implementation of an item for a tree. Our `treemodel` is designed to work with this class and it's subclasses."""
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
        return 1

    def data(self, role: int) -> typing.Any:
        try:
            return self._itemData[role]
        except KeyError:
            return None

    def setData(self, role: int, data: typing.Any):
        self._itemData[role] = data

    def parent(self) -> TreeItem:
        return self._parentItem

    def row(self) -> int:
        """Return which row we are with respect to the parent."""
        if self._parentItem:
            return self._parentItem._childItems.index(self)
        else:
            return None

    def iterateChildren(self) -> typing.Generator[TreeItem]:
        """Recursively iterate through all children of this step"""
        for child in self._childItems:
            yield child
            yield from child.iterateChildren()


class SelfTreeItem(TreeItem):
    """A tree item which returns itself as as its own DisplayRole data"""
    def __init__(self):
        super().__init__()
        self.setData(QtCore.Qt.DisplayRole, self)
