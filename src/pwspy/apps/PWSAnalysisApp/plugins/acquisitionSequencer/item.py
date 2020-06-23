from io import UnsupportedOperation


class TreeItem:
    def __init__(self):
        self._parentItem = None
        self._itemData = {}
        self._childItems = []

    def addChild(self, item):
        item._parentItem = self
        self._childItems.append(item)

    def addChildren(self, children):
        for i in children:
            i._parentItem = self
        self._childItems.extend(children)

    def child(self, row):
        return self._childItems[row]

    def childCount(self):
        return len(self._childItems)

    def columnCount(self):
        return len(self._itemData)

    def data(self, column):
        try:
            return self._itemData[column]
        except KeyError:
            return None

    def setData(self, column, data):
        self._itemData[column] = data

    def parent(self):
        if self._parentItem is None: return 0 # Documentation says to return 0 rather than None.
        return self._parentItem

    def row(self):
        if self._parentItem:
            return self._parentItem._childItems.index(self)
        return None


class SelfTreeItem(TreeItem):
    def columnCount(self): return 1
    def data(self, column): return self
    def setData(self, column, data): raise UnsupportedOperation()
