from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QFrame, QScrollArea, QGridLayout, QSizePolicy, QLayout


class CollapsibleSection(QWidget):
    stateChanged = QtCore.pyqtSignal(bool)

    def __init__(self, title, animationDuration, parent: QWidget):
        super().__init__(parent)
        self._animationDuration = animationDuration
        self._toggleButton = QCheckBox(title, self)
        headerLine = QFrame(self)
        self._toggleAnimation = QtCore.QParallelAnimationGroup(self)
        self._contentArea = QScrollArea(self)
        mainLayout = QGridLayout(self)

        self._toggleButton.setCheckable(True)
        self._toggleButton.setChecked(True)

        headerLine.setFrameShape(QFrame.HLine)
        headerLine.setFrameShadow(QFrame.Sunken)
        headerLine.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self._contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # start out collapsed
        self._contentArea.setMaximumHeight(0)
        self._contentArea.setMinimumHeight(0)

        # let the entire widget grow and shrink with its content
        self._toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"minimumHeight"))
        self._toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"maximumHeight"))
        self._toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self._contentArea, b"maximumHeight"))

        mainLayout.setVerticalSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)

        mainLayout.addWidget(self._toggleButton, 0, 0, 1, 1, QtCore.Qt.AlignLeft)

        mainLayout.addWidget(headerLine, 1, 2, 1, 1)

        mainLayout.addWidget(self._contentArea, 1, 0, 1, 3)

        self.setLayout(mainLayout)
        self.setLayout = self._setLayout

        self._toggleButton.toggled.connect(
            lambda checked:
            [  # self.toggleButton.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow),
                self._toggleAnimation.setDirection(
                    QtCore.QAbstractAnimation.Forward if not checked else QtCore.QAbstractAnimation.Backward),
                self._toggleAnimation.start()])
        self._toggleAnimation.finished.connect(lambda: self.stateChanged.emit(self._toggleButton.isChecked()))

    def checkState(self):
        return self._toggleButton.checkState()

    def setCheckState(self, state: bool):
        self._toggleButton.setCheckState(state)

    def _setLayout(self, contentLayout: QLayout):
        oldLayout = self._contentArea.layout()
        del oldLayout
        self._contentArea.setLayout(contentLayout)
        collapsedHeight = self.sizeHint().height() - self._contentArea.maximumHeight()
        contentHeight = contentLayout.sizeHint().height()
        for i in range(self._toggleAnimation.animationCount() - 1):
            SectionAnimation = self._toggleAnimation.animationAt(i)
            SectionAnimation.setDuration(self._animationDuration)
            SectionAnimation.setStartValue(collapsedHeight)
            SectionAnimation.setEndValue(collapsedHeight + contentHeight)

        contentAnimation = self._toggleAnimation.animationAt(self._toggleAnimation.animationCount() - 1)
        contentAnimation.setDuration(self._animationDuration)
        contentAnimation.setStartValue(0)
        contentAnimation.setEndValue(contentHeight)