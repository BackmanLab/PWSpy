import typing

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QTableWidget, QAbstractItemView, QApplication, QTableWidgetItem, QPushButton, QMenu

from pwspy.imCube.ICMetaDataClass import ICMetaData


class CopyableTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.ContiguousSelection)

    def keyPressEvent(self, event):
        if event.matches(QtGui.QKeySequence.Copy):
            self.copy()
        else:
            super().keyPressEvent(event)

    def copy(self):
        try:
            sel = self.selectedRanges()[0]
            t = '\t'.join(
                [self.horizontalHeaderItem(i).text() for i in range(sel.leftColumn(), sel.rightColumn() + 1)]) + '\n'
            for i in range(sel.topRow(), sel.bottomRow() + 1):
                for j in range(sel.leftColumn(), sel.rightColumn() + 1):
                    if t[-1] != '\n': t += '\t'
                    item = self.item(i, j)
                    t += ' ' if item is None else item.text()
                t += '\n'
            QApplication.clipboard().setText(t)
        except Exception as e:
            print("Copy Failed: ", e)


class NumberTableWidgetItem(QTableWidgetItem):
    def __init__(self, num: float):
        super().__init__(str(num))
        num = float(num)  # in case the constructor is called with a string.
        self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)  # read only
        self.number = num

    def __lt__(self, other: 'NumberTableWidgetItem'):
        return self.number < other.number

    def __gt__(self, other: 'NumberTableWidgetItem'):
        return self.number > other.number


class CellTableWidgetItem:
    cube: ICMetaData

    def __init__(self, cube: ICMetaData, label: str, num: int):
        self.cube = cube
        self.num = num
        self.notesButton = QPushButton("Open")
        self.notesButton.setFixedSize(40, 30)
        self.path = QTableWidgetItem(label)
        self.numLabel = NumberTableWidgetItem(num)
        self.roiLabel = NumberTableWidgetItem(len(cube.getMasks()))
        self.anLabel = NumberTableWidgetItem(len(cube.getAnalyses()))
        self.notesButton.released.connect(self.editNotes)
        self._items = [self.path, self.numLabel, self.roiLabel, self.anLabel]
        self._invalid = False
        self._reference = False

    def editNotes(self):
        self.cube.editNotes()

    def setInvalid(self, invalid: bool):
        if invalid:
            self._setItemColor(QtCore.Qt.red)
            self._reference = False
        else:
            self._setItemColor(QtCore.Qt.white)
        self._invalid = invalid

    def setReference(self, reference: bool) -> None:
        if self.isInvalid():
            return
        if reference:
            self._setItemColor(QtCore.Qt.green)
        else:
            self.__setItemColor(QtCore.Qt.white)
        self._reference = reference

    def _setItemColor(self, color):
        for i in self._items:
            i.setBackground(color)

    def isInvalid(self) -> bool:
        return self._invalid

    def isReference(self) -> bool:
        return self._reference


class CellTableWidget(QTableWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        columns = ('Path', 'Cell#', 'ROIs', 'Analyses', 'Notes')
        self.setRowCount(0)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.verticalHeader().hide()
        [self.setColumnWidth(i, w) for i, w in zip(range(len(columns)), [60, 40, 40, 50, 40])]
        self.cellItems = []

    def showContextMenu(self, point: QtCore.QPoint):
        menu = QMenu("Context Menu")
        state = not self.selectedCellItems[0].isInvalid()
        stateString = "Disable Cell(s)" if state else "Enable Cell(s)"
        refState = not self.selectedCellItems[0].isReference()
        refStateString = "Set as Reference" if refState else "Unset as Reference"
        invalidAction = menu.addAction(stateString)
        invalidAction.triggered.connect(lambda: self.toggleSelectedCellsInvalid(state))
        refAction = menu.addAction(refStateString)
        refAction.triggered.connect(lambda: self.toggleSelectedCellsReference(refState))
        menu.exec(self.mapToGlobal(point))

    def toggleSelectedCellsInvalid(self, state: bool):
        for i in self.selectedCellItems:
            i.setInvalid(state)

    def toggleSelectedCellsReference(self, state: bool) -> None:
        for i in self.selectedCellItems:
            i.setReference(state)

    @property
    def selectedCellItems(self) -> typing.List[CellTableWidgetItem]:
        """Returns the rows that have been selected."""
        rowIndices = [i.row() for i in self.selectedIndexes()[::self.columnCount()]]
        rowIndices.sort()
        return [self.cellItems[i] for i in rowIndices]

    @property
    def enabledCells(self) -> typing.List[CellTableWidgetItem]:
        return [i for i in self.cellItems if not i.isInvalid()]

    def addCellItem(self, item: CellTableWidgetItem) -> None:
        row = len(self.cellItems)
        self.setSortingEnabled(
            False)  # The fact that we are adding items assuming its the last row is a problem is sorting is on.
        self.setRowCount(row + 1)
        self.setItem(row, 0, item.path)
        self.setItem(row, 1, item.numLabel)
        self.setItem(row, 2, item.roiLabel)
        self.setItem(row, 3, item.anLabel)
        self.setCellWidget(row, 4, item.notesButton)
        self.setSortingEnabled(True)
        self.cellItems.append(item)

    def clearCellItems(self) -> None:
        self.setRowCount(0)
        self.cellItems = []