from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget


class AspectRatioWidget(QWidget):
    def __init__(self, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self._aspect = aspect

    def resizeEvent(self, event: QtGui.QResizeEvent):
        w, h = event.size().width(), event.size().height()
        self._resize(w, h)

    def _resize(self, width, height):
        newHeight = width / self._aspect
        newWidth = height * self._aspect
        if newHeight * self._aspect > newWidth:
            self.setMaximumWidth(newWidth)
            self.setMaximumHeight(1000000)
        else:
            self.setMaximumHeight(newHeight)
            self.setMaximumWidth(1000000)

    def setAspect(self, aspect: float):
        self._aspect = aspect
        self._resize(self.width(), self.height())
