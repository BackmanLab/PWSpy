from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QTableWidget, QAbstractItemView, QApplication, QTableWidgetItem


class CopyableTable(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setSelectionMode(QAbstractItemView.ContiguousSelection)
        self.setSelectionMode = lambda: (_ for _ in ()).throw(NotImplementedError("The CopyableTable class requires the selection mode to remain as `contiguous`"))


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
    """This table widget item will be sorted numerically rather than alphabetically (1, 10, 11, 2, ...)"""
    def __init__(self, num: float):
        super().__init__(str(num))
        num = float(num)  # in case the constructor is called with a string.
        self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)  # read only
        self.number = num

    def __lt__(self, other: 'NumberTableWidgetItem'):
        return self.number < other.number

    def __gt__(self, other: 'NumberTableWidgetItem'):
        return self.number > other.number


