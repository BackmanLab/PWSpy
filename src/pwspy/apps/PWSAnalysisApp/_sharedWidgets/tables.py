from __future__ import annotations
from datetime import datetime

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QTableWidget, QAbstractItemView, QApplication, QTableWidgetItem

import pwspy
import numpy as np

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
                [self.horizontalHeaderItem(i).text() for i in range(sel.leftColumn(), sel.rightColumn() + 1) if not self.isColumnHidden(i)]) + '\n'
            for i in range(sel.topRow(), sel.bottomRow() + 1):
                for j in range(sel.leftColumn(), sel.rightColumn() + 1):
                    if not self.isColumnHidden(j):
                        if t[-1] != '\n': t += '\t'
                        item = self.item(i, j)
                        t += ' ' if item is None else item.text()
                t += '\n'
            QApplication.clipboard().setText(t)
        except Exception as e:
            print("Copy Failed: ", e)


class NumberTableWidgetItem(QTableWidgetItem):
    """This table widget item will be sorted numerically rather than alphabetically (1, 10, 11, 2, ...)"""
    def __init__(self, num: float = None):
        if num is None:
            super().__init__("None")
            num = -np.inf
        else:
            super().__init__(str(num))
            num = float(num)  # in case the constructor is called with a string.
        self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)  # read only
        self.number = num

    def __lt__(self, other: 'NumberTableWidgetItem'):
        return self.number < other.number

    def __gt__(self, other: 'NumberTableWidgetItem'):
        return self.number > other.number

    def setNumber(self, num: float):
        self.number = num
        self.setText(str(num))


class DatetimeTableWidgetItem(QTableWidgetItem):
    """This table widget item will be sorted chronologically rather than alphabetically."""
    def __init__(self, dtime: datetime):
        if isinstance(dtime, str):
            dtime = datetime.strptime(dtime, pwspy.dateTimeFormat) #If constructor called with a string convert to datetime.
        super().__init__(datetime.strftime(dtime, pwspy.dateTimeFormat))
        self.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)  # read only
        self.dtime = dtime

    def __lt__(self, other: DatetimeTableWidgetItem):
        return self.dtime < other.dtime

    def __gt__(self, other: DatetimeTableWidgetItem):
        return self.dtime > other.dtime
