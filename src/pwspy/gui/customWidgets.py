# -*- coding: utf-8 -*-
"""
Created on Mon Feb 11 21:22:01 2019

@author: Nick
"""
import typing

import numpy as np
from PyQt5 import (QtGui, QtCore)
from PyQt5.QtWidgets import (QWidget, QApplication, QGridLayout,
                             QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QMenu, QPushButton, QFrame, QScrollArea, QLayout, QSizePolicy,
                             QCheckBox)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from matplotlib.figure import Figure
from pwspy.imCube.ImCubeClass import ImCube, FakeCube
from pwspy.utility import PlotNd


class LittlePlot(FigureCanvas):
    def __init__(self):
        #        self.setLayout(QGraphicsLinearLayout())
        self.fig = Figure()
        self.data = np.ones((100, 100)) * np.sin(np.linspace(1, 6, num=100))[None, :]
        ax = self.fig.add_subplot(1, 1, 1)
        ax.imshow(self.data)
        ax.yaxis.set_visible(False)
        ax.xaxis.set_visible(False)
        #        canvas = FigureCanvas(self.fig)
        super().__init__(self.fig)
        #        self.layout().addWidget(canvas)
        #        self.setFixedSize(200,200)
        self.mpl_connect("button_release_event", self.mouseReleaseEvent)
        self.setMaximumWidth(200)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            BigPlot(self.data)


class BigPlot(QWidget):
    def __init__(self, data):
        super().__init__()
        self.setLayout(QGridLayout())
        self.fig = Figure()
        ax = self.fig.add_subplot(1, 1, 1)
        ax.imshow(data)
        canvas = FigureCanvas(self.fig)
        self.layout().addWidget(canvas)
        self.layout().addWidget(NavigationToolbar(canvas, self))
        self.show()


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


class CellTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        columns = ('Cell', 'ROIs', 'Analyses', 'Notes', 'Plots')
        self.setRowCount(5)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.verticalHeader().hide()
        [self.setColumnWidth(i, w) for i, w in zip(range(len(columns)), [60, 40, 40, 40, 40])]
        self.cells = []
        '''Test'''
        for j in range(self.rowCount()):
            self.cells.append(CellTableWidgetItem(self, j, FakeCube(j), j))

    #        self.table.setItem(1,1,QTableWidgetItem("rms"))
    def showContextMenu(self, point: QtCore.QPoint):
        menu = QMenu("Context Menu")
        action = menu.addAction("Disable cell")
        action.triggered.connect(self.toggleSelectedCellsInvalid)
        menu.exec(self.mapToGlobal(point))

    def toggleSelectedCellsInvalid(self):
        sel = self.selectedCells()
        state = not sel[0].isInvalid()
        for i in sel:
            i.setInvalid(state)

    def selectedCells(self) -> typing.List[int]:
        """Returns the rows that have been selected."""
        rowIndices = [i.row() for i in self.selectedIndexes()[::self.columnCount()]]
        rowIndices.sort()
        return [self.cells[i] for i in rowIndices]


class CellTableWidgetItem:
    def __init__(self, parent: CellTableWidget, row: int, cube: ImCube, num: int):
        #        super().__init__()
        self.cube = cube
        self.parent = parent
        self.row = row
        self.plotsButton = QPushButton("Show")
        self.plotsButton.setFixedSize(40, 30)
        self.notesButton = QPushButton("Open")
        self.notesButton.setFixedSize(40, 30)
        self.label = QTableWidgetItem(cube.filePath)

        self.plotsButton.released.connect(self.showPlotsMenu)
        self.notesButton.released.connect(self.editNotes)

        self.parent.setItem(row, 0, self.label)
        self.parent.setItem(row, 1, QTableWidgetItem(str(3)))  # len(cube.getMasks())))
        self.parent.setItem(row, 2, QTableWidgetItem(str(1)))
        self.parent.setCellWidget(row, 3, self.notesButton)
        self.parent.setCellWidget(row, 4, self.plotsButton)

        self._invalid = False

    def showPlotsMenu(self):
        menu = QMenu("ContextMenu")
        action = menu.addAction('3D')
        action.triggered.connect(lambda: PlotNd(self.cube.data))
        menu.exec(QtGui.QCursor.pos())

    def editNotes(self):
        self.cube.editNotes()

    def setInvalid(self, invalid: bool):
        if invalid:
            self.label.setBackground(QtCore.Qt.red)
        else:
            self.label.setBackground(QtCore.Qt.white)
        self._invalid = invalid

    def isInvalid(self) -> bool:
        return self._invalid


class CollapsibleSection(QWidget):
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
        self.setLayout = self.setLayout_

        self.toggleButton.toggled.connect(
            lambda checked:
            [  # self.toggleButton.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow),
                self.toggleAnimation.setDirection(
                    QtCore.QAbstractAnimation.Forward if not checked else QtCore.QAbstractAnimation.Backward),
                self.toggleAnimation.start()])

    def setLayout_(self, contentLayout: QLayout):
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
