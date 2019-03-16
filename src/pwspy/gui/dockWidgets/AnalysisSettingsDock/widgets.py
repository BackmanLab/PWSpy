from PyQt5.QtGui import QValidator, QDoubleValidator
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QSpacerItem, QSizePolicy, QLayout
from PyQt5 import QtCore


class VerticallyCompressedWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setLayout(QVBoxLayout())
        self._contentsFrame = QFrame()
        spacer = QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout().addWidget(self._contentsFrame)
        self.layout().addItem(spacer)
        self.layout = self._layout # override methods
        self.setLayout = self._setLayout

    def _layout(self) -> QLayout:
        return self._contentsFrame.layout()

    def _setLayout(self, layout: QLayout):
        self._contentsFrame.setLayout(layout)


class LinearityValidator(QValidator):
    stateChanged = QtCore.pyqtSignal(QValidator.State)

    def __init__(self):
        super().__init__()
        self.doubleValidator = QDoubleValidator()
        self.state = QValidator.Acceptable

    def validate(self, inp: str, pos: int):
        oldState = self.state
        for i in inp.split(','):
            ret = self.doubleValidator.validate(i, pos)
            if ret[0] == QValidator.Intermediate:
                self.state = ret[0]
                if self.state != oldState: self.stateChanged.emit(self.state)
                return self.state, inp, pos
            elif ret[0] == QValidator.Invalid:
                return ret
        self.state = QValidator.Acceptable
        if self.state != oldState: self.stateChanged.emit(self.state)
        return self.state, inp, pos
