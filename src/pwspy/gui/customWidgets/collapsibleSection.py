from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QCheckBox, QFrame, QScrollArea, QGridLayout, QSizePolicy, QLayout


class CollapsibleSection(QWidget):
    stateChanged = QtCore.pyqtSignal(bool)

    def __init__(self, title, animationDuration, parent: QWidget):
        super().__init__(parent)
        self.animationDuration = animationDuration
        self.toggleButton = QCheckBox(title, self)
        headerLine = QFrame(self)
        self.toggleAnimation = QtCore.QParallelAnimationGroup(self)
        self.contentArea = QScrollArea(self)
        mainLayout = QGridLayout(self)

        self.toggleButton.setCheckable(True)
        self.toggleButton.setChecked(True)

        headerLine.setFrameShape(QFrame.HLine)
        headerLine.setFrameShadow(QFrame.Sunken)
        headerLine.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        self.contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        # start out collapsed
        self.contentArea.setMaximumHeight(0)
        self.contentArea.setMinimumHeight(0)

        # let the entire widget grow and shrink with its content
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"minimumHeight"))
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"maximumHeight"))
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self.contentArea, b"maximumHeight"))

        mainLayout.setVerticalSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)

        mainLayout.addWidget(self.toggleButton, 0, 0, 1, 1, QtCore.Qt.AlignLeft)

        mainLayout.addWidget(headerLine, 1, 2, 1, 1)

        mainLayout.addWidget(self.contentArea, 1, 0, 1, 3)

        self.setLayout(mainLayout)
        self.setLayout = self._setLayout

        self.toggleButton.toggled.connect(
            lambda checked:
            [  # self.toggleButton.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow),
                self.toggleAnimation.setDirection(
                    QtCore.QAbstractAnimation.Forward if not checked else QtCore.QAbstractAnimation.Backward),
                self.toggleAnimation.start()])
        self.toggleAnimation.finished.connect(lambda: self.stateChanged.emit(self.toggleButton.isChecked()))

    def checkState(self):
        return self.toggleButton.checkState()

    def setCheckState(self, state: bool):
        self.toggleButton.setCheckState(state)

    def _setLayout(self, contentLayout: QLayout):
        oldLayout = self.contentArea.layout()
        del oldLayout
        self.contentArea.setLayout(contentLayout)
        collapsedHeight = self.sizeHint().height() - self.contentArea.maximumHeight()
        contentHeight = contentLayout.sizeHint().height()
        for i in range(self.toggleAnimation.animationCount() - 1):
            SectionAnimation = self.toggleAnimation.animationAt(i)
            SectionAnimation.setDuration(self.animationDuration)
            SectionAnimation.setStartValue(collapsedHeight)
            SectionAnimation.setEndValue(collapsedHeight + contentHeight)

        contentAnimation = self.toggleAnimation.animationAt(self.toggleAnimation.animationCount() - 1)
        contentAnimation.setDuration(self.animationDuration)
        contentAnimation.setStartValue(0)
        contentAnimation.setEndValue(contentHeight)