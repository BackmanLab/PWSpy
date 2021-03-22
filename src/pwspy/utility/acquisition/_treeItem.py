from __future__ import annotations
import typing


class TreeItem:
    """Basic implementation of an item for a tree. Our `treemodel` subclassed from QAbstractItemModel is designed to work with this class and it's subclasses."""
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

    def getTreePath(self) -> typing.Tuple[TreeItem]:
        """Return a list of steps starting with the root step and ending with this step."""
        l: typing.List[TreeItem] = []
        step = self
        while True:
            l.append(step)
            if step._parentItem is None:
                break
            step = step._parentItem
        return tuple(reversed(l))

    def data(self, role: int) -> typing.Any:
        try:
            return self._itemData[role]
        except KeyError:
            return None

    def setData(self, role: int, data: typing.Any):
        self._itemData[role] = data

