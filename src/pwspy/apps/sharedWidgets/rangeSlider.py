# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

import sys, os
import typing
from numbers import Number
from typing import Tuple
import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

__all__ = ['QRangeSlider']

from PyQt5.QtGui import QColor

from PyQt5.QtWidgets import QHBoxLayout, QWidget, QGridLayout, QSplitter

DEFAULT_CSS= """
QRangeSlider * {
    border: 0px;
    padding: 0px;
}

QRangeSlider #Head {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #222, stop:1 #333);
}
QRangeSlider #Span:active {
    background: #339099;
}
QRangeSlider #Tail {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #222, stop:1 #333);
}
QRangeSlider > QSplitter::handle {
    background: #d42a04;
}
QRangeSlider > QSplitter::handle:vertical {
    height: 4px;
}
QRangeSlider > QSplitter::handle:pressed {
    background: #691401;
}
"""


def scale(val: Number, src: Tuple[Number, Number], dst: Tuple[Number, Number]):
    """src is a tuple containing the original minimum and maximum values.
    dst is a tuple containing the new min and max values.
    This function will return the value of val scaled from src to dst"""
    if src[1] == src[0]: #These cases will result in a nan value.
        return (dst[1] + dst[0])/2
    elif dst[0] == dst[1]:
        return dst[0]
    else:
        return float(((val - src[0]) / float(src[1]-src[0])) * (dst[1]-dst[0]) + dst[0])


class Element(QtWidgets.QWidget):
    def __init__(self, main):
        super().__init__()
        self.main = main
        self._textColor = QtGui.QColor(125, 125, 125)

    def textColor(self) -> QtGui.QColor:
        return self._textColor

    def setTextColor(self, color: typing.Union[int, typing.Tuple[int, int, int]]):
        if type(color) == tuple and len(color) == 3:
            self._textColor = QtGui.QColor(color[0], color[1], color[2])
        elif type(color) == int:
            self._textColor = QtGui.QColor(color, color, color)

    def paintEvent(self, event):
        qp = QtGui.QPainter(self)
        if self.main.drawValues():
            self.drawText(event, qp)

    def drawText(self, event, painter):
        pass #Override this to draw text.

    def setStyleSheet(self, styleSheet: str) -> None:
        super().setStyleSheet(styleSheet)
        self.setAutoFillBackground(True) # For some reason if this isn't done then setting the stylesheet turns everything gray.


def numFormat(num: Number) -> str:
    num = np.abs(num)
    if num < 1 or num>=1000:
        return f"{num:.2E}"
    else:
        return f"{num:.2f}"


class Head(Element):
    def __init__(self, main):
        super(Head, self).__init__(main)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont('Arial', 10))
        qp.drawText(event.rect(), QtCore.Qt.AlignLeft, numFormat(self.main.min()))


class Tail(Element):
    def __init__(self, main):
        super(Tail, self).__init__(main)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont('Arial', 10))
        qp.drawText(event.rect(), QtCore.Qt.AlignRight, numFormat(self.main.max()))


class Handle(Element):
    def __init__(self, main):
        super(Handle, self).__init__(main)

    def drawText(self, event, qp):
        qp.setPen(self.textColor())
        qp.setFont(QtGui.QFont('Arial', 10))
        qp.drawText(event.rect(), QtCore.Qt.AlignLeft, numFormat(self.main.start()))
        qp.drawText(event.rect(), QtCore.Qt.AlignRight, numFormat(self.main.end()))

    def mouseMoveEvent(self, event):
        event.accept()
        mx = event.globalX()
        _mx = getattr(self, '__mx', None)
        if not _mx:
            setattr(self, '__mx', mx)
            dx = 0
        else:
            dx = mx - _mx
        setattr(self, '__mx', mx)
        if dx == 0:
            event.ignore()
            return
        elif dx > 0:
            dx = 1
        elif dx < 0:
            dx = -1
        s = self.main.start() + dx
        e = self.main.end() + dx
        if s >= self.main.min() and e <= self.main.max():
            self.main.setRange(s, e)


class QRangeSlider(QtWidgets.QWidget):
    endValueChanged = QtCore.pyqtSignal(int)
    maxValueChanged = QtCore.pyqtSignal(int)
    minValueChanged = QtCore.pyqtSignal(int)
    startValueChanged = QtCore.pyqtSignal(int)

    _SPLIT_START = 1
    _SPLIT_END = 2

    def __init__(self, parent=None):
        super(QRangeSlider, self).__init__(parent)
        # setup Ui
        self.resize(300, 30)
        self.gridLayout = QtWidgets.QGridLayout(self)
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.gridLayout.setSpacing(0)
        self._splitter = QtWidgets.QSplitter(self)
        self._splitter.setMinimumSize(QtCore.QSize(0, 0))
        self._splitter.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self._splitter.setOrientation(QtCore.Qt.Horizontal)
        self.gridLayout.addWidget(self._splitter, 0, 0, 1, 1)
        self.head = Head(main=self)  #The order that these are added matters.
        self.head.setObjectName("Head") # These names are used by the stylesheet
        self.handle = Handle(main=self)
        self.handle.setObjectName("Span")
        self.tail = Tail(main=self)
        self.tail.setObjectName("Tail")
        self.setMinimumHeight(15)

        self._splitter.addWidget(self.head)
        self._splitter.addWidget(self.handle)
        self._splitter.addWidget(self.tail)

        self.setStyleSheet(DEFAULT_CSS)

        self.setMouseTracking(False)  # Don't fire mouse events unless a button is clicked.
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self.handle.setTextColor((150, 255, 150))
        self._setMin(0)
        self._setMax(99)
        self.setStart(0)
        self.setEnd(99)
        self.setDrawValues(True)

    def showEvent(self, evt):
        self.head.setAutoFillBackground(True) #IDK why but the colors from the stylesheet won't fill in if we don't do this.
        self.tail.setAutoFillBackground(True)
        self.handle.setAutoFillBackground(True)
        super().showEvent(evt)

    def min(self):
        return getattr(self, '__min', None)

    def max(self):
        return getattr(self, '__max', None)

    def _setMin(self, value):
        setattr(self, '__min', value)
        self.minValueChanged.emit(value)

    def setMin(self, value):
        self._setMin(value)
        if self.start() < value:
            self._setStart(value)

    def _setMax(self, value):
        setattr(self, '__max', value)
        self.maxValueChanged.emit(value)

    def setMax(self, value):
        self._setMax(value)
        if self.end() > value:
            self._setEnd(value)

    def start(self):
        return getattr(self, '__start', None)

    def end(self):
        return getattr(self, '__end', None)

    def _setStart(self, value):
        setattr(self, '__start', value)
        self.startValueChanged.emit(value)

    def setStart(self, value):
        v = self._valueToPos(value)
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_START)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setStart(value)

    def _setEnd(self, value):
        setattr(self, '__end', value)
        self.endValueChanged.emit(value)

    def setEnd(self, value):
        v = self._valueToPos(value)
        self._splitter.splitterMoved.disconnect()
        self._splitter.moveSplitter(v, self._SPLIT_END)
        self._splitter.splitterMoved.connect(self._handleMoveSplitter)
        self._setEnd(value)

    def drawValues(self):
        return getattr(self, '__drawValues', None)

    def setDrawValues(self, draw):
        setattr(self, '__drawValues', draw)

    def getRange(self):
        return self.start(), self.end()

    def setRange(self, start, end):
        self.setStart(start)
        self.setEnd(end)

    def keyPressEvent(self, event):
        key = event.key()
        if key == QtCore.Qt.Key_Left:
            s = self.start()-1
            e = self.end()-1
        elif key == QtCore.Qt.Key_Right:
            s = self.start()+1
            e = self.end()+1
        else:
            event.ignore()
            return
        event.accept()
        if s >= self.min() and e <= self.max():
            self.setRange(s, e)

    def setBackgroundStyle(self, style):
        self.tail.setStyleSheet(style)
        self.head.setStyleSheet(style)

    def _valueToPos(self, value):
        s = scale(value, (self.min(), self.max()), (0, self.width()))
        return int(s)

    def _posToValue(self, xpos):
        return scale(xpos, (0, self.width()), (self.min(), self.max()))

    def _handleMoveSplitter(self, xpos, index):
        hw = self._splitter.handleWidth()
        def _lockWidth(widget):
            width = widget.size().width()
            widget.setMinimumWidth(width)
            widget.setMaximumWidth(width)
        def _unlockWidth(widget):
            widget.setMinimumWidth(0)
            widget.setMaximumWidth(16777215)
        v = self._posToValue(xpos)
        if index == self._SPLIT_START:
            _lockWidth(self.tail)
            if v >= self.end():
                return
            offset = -20
            w = xpos + offset
            self._setStart(v)
        elif index == self._SPLIT_END:
            _lockWidth(self.head)
            if v <= self.start():
                return
            offset = -40
            w = self.width() - xpos + offset
            self._setEnd(v)
        _unlockWidth(self.tail)
        _unlockWidth(self.head)
        _unlockWidth(self.handle)

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    rs = QRangeSlider()
    rs.show()

    rs.setMax(100)
    rs.setMin(0.015)
    rs.setRange(.017, .50)
    rs.setBackgroundStyle('background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #222, stop:1 #333);')
    rs.handle.setStyleSheet('background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282, stop:1 #393);')
    app.exec_()