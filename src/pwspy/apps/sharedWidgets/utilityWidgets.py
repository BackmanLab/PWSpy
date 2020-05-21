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

from PyQt5 import QtGui, QtCore
from PyQt5.QtWidgets import QWidget, QWIDGETSIZE_MAX


class AspectRatioWidget(QWidget):
    def __init__(self, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self._aspect = aspect

    def resizeEvent(self, event: QtGui.QResizeEvent):
        w, h = event.size().width(), event.size().height()
        self._resize(w, h)

    def _resize(self, width, height):
        newHeight = width / self._aspect #The ideal height based on the new commanded width
        newWidth = height * self._aspect #the ideal width based on the new commanded height
        #Now determine which of the new dimensions to use.
        if width > newWidth:
            self.setMaximumWidth(newWidth)
            self.setMaximumHeight(QWIDGETSIZE_MAX)
        else:
            self.setMaximumHeight(newHeight)
            self.setMaximumWidth(QWIDGETSIZE_MAX)

    def setAspect(self, aspect: float):
        self._aspect = aspect
        self._resize(self.width(), self.height())
