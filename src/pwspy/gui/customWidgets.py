# -*- coding: utf-8 -*-
"""
Created on Mon Feb 11 21:22:01 2019

@author: Nick
"""
import os.path as osp
import typing

import numpy as np
from PyQt5 import (QtGui, QtCore)
from PyQt5.QtWidgets import (QWidget, QApplication, QGridLayout,
                             QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QMenu, QPushButton, QFrame, QScrollArea, QLayout, QSizePolicy,
                             QCheckBox,
                             QBoxLayout, QSpacerItem, QButtonGroup)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from matplotlib.widgets import LassoSelector

from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.imCube.ImCubeClass import ImCube
from pwspy.imCube.matplotlibwidg import myLasso


class LittlePlot(FigureCanvas):
    def __init__(self, data: np.ndarray, cell: ICMetaData):
        assert len(data.shape) == 2
        self.fig = Figure()
        self.data = data
        self.cell = cell
        ax = self.fig.add_subplot(1, 1, 1)
        ax.imshow(self.data)
        ax.set_title(osp.split(cell.filePath)[-1])
        ax.yaxis.set_visible(False)
        ax.xaxis.set_visible(False)
        super().__init__(self.fig)
        #        self.layout().addWidget(canvas)
        #        self.setFixedSize(200,200)
        self.mpl_connect("button_release_event", self.mouseReleaseEvent)
        self.setMaximumWidth(200)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            BigPlot(self, self.data)


class BigPlot(QWidget):
    def __init__(self, parent, data):
        super().__init__(parent, QtCore.Qt.Window)
        self.setWindowTitle("What?!")
        layout = QGridLayout()
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.imshow(data)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.buttonGroup = QButtonGroup(self)
        self.lassoButton = QPushButton("L")
        self.ellipseButton = QPushButton("O")
        self.lastButton_ = None
        self.buttonGroup.addButton(self.lassoButton, 1)
        self.buttonGroup.addButton(self.ellipseButton)
        self.buttonGroup.buttonReleased.connect(self.handleButtons)
        [i.setCheckable(True) for i in self.buttonGroup.buttons()]

        layout.addWidget(self.lassoButton, 0, 0, 1, 1)
        layout.addWidget(self.ellipseButton, 0, 1, 1, 1)
        layout.addWidget(self.canvas, 1, 0, 8, 8)
        layout.addWidget(NavigationToolbar(self.canvas, self), 10, 0, 8, 8)
        self.setLayout(layout)

        self.selector = None

        self.show()

    def handleButtons(self, button):
        if button != self.lastButton_:
            if button is self.lassoButton:
                self.selector = myLasso(self.ax)
            elif button is self.ellipseButton:
                self.selector = LassoSelector(self.ax)
            self.lastButton_ = button


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
        self.notesButton.released.connect(self.editNotes)

        self._invalid = False
        self._reference = False

    def editNotes(self):
        self.cube.editNotes()

    def setInvalid(self, invalid: bool):
        if invalid:
            self.path.setBackground(QtCore.Qt.red)
        else:
            self.path.setBackground(QtCore.Qt.white)
            self._reference = False
        self._invalid = invalid

    def setReference(self, reference: bool) -> None:
        if self.isInvalid():
            return
        if reference:
            self.path.setBackground(QtCore.Qt.green)
        else:
            self.path.setBackground(QtCore.Qt.white)
        self._reference = reference

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
        self.setItem(row, 2, QTableWidgetItem(str(3)))  # len(cube.getMasks())))
        self.setItem(row, 3, QTableWidgetItem(str(1)))
        self.setCellWidget(row, 4, item.notesButton)
        self.setSortingEnabled(True)
        self.cellItems.append(item)

    def clearCellItems(self) -> None:
        self.setRowCount(0)
        self.cellItems = []


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

    def _setLayout(self, contentLayout: QLayout):
        oldLayout = self.contentArea.layout()
        del oldLayout
        self.contentArea.setLayout(contentLayout)
        collapsedHeight = self.sizeHint().height() - self.contentArea.maximumHeight()
        contentHeight = contentLayout.sizeHint().height()
        print(contentHeight)
        for i in range(self.toggleAnimation.animationCount() - 1):
            SectionAnimation = self.toggleAnimation.animationAt(i)
            SectionAnimation.setDuration(self.animationDuration)
            SectionAnimation.setStartValue(collapsedHeight)
            SectionAnimation.setEndValue(collapsedHeight + contentHeight)

        contentAnimation = self.toggleAnimation.animationAt(self.toggleAnimation.animationCount() - 1)
        contentAnimation.setDuration(self.animationDuration)
        contentAnimation.setStartValue(0)
        contentAnimation.setEndValue(contentHeight)


class AspectRatioWidget(QWidget):
    def __init__(self, widget: QWidget, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self.aspect = aspect
        self.layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.widget = widget
        # add spacer, then your widget, then spacer
        self.layout.addItem(QSpacerItem(0, 0))
        self.layout.addWidget(widget)
        self.layout.addItem(QSpacerItem(0, 0))

    def resizeEvent(self, event: QtGui.QResizeEvent):
        thisAspectRatio = event.size().width() / event.size().height()

        if thisAspectRatio > self.aspect:  # too wide
            self.layout.setDirection(QBoxLayout.LeftToRight)
            widgetStretch = self.height() * self.aspect  # i.e., my width
            outerStretch = (self.width() - widgetStretch) / 2 + 0.5
        else:  # too tall
            self.layout.setDirection(QBoxLayout.TopToBottom)
            widgetStretch = self.width() * (1 / self.aspect)  # i.e., my height
            outerStretch = (self.height() - widgetStretch) / 2 + 0.5

        self.layout.setStretch(0, outerStretch)
        self.layout.setStretch(1, widgetStretch)
        self.layout.setStretch(2, outerStretch)

    def setAspect(self, aspect: float):
        self.aspect = aspect
