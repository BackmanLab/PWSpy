from PyQt5.QtGui import QValidator, QDoubleValidator
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFrame, QSpacerItem, QSizePolicy, QLayout


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
    allowedChars = '0123456789,.- '

    def __init__(self):
        super().__init__()
        self.doubleValidator = QDoubleValidator()

    def validate(self, input: str, pos: int):
        for i in input:
            if i not in self.allowedChars:
                return (QValidator.Invalid, input, 0)
        for i in input.split(','):
            ret = self.doubleValidator.validate(i, pos)
            if  ret == QValidator.Acceptable:
                return (ret, input, pos)
        return (QValidator.Acceptable, input, pos)
