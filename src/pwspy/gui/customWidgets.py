# -*- coding: utf-8 -*-
"""
Created on Mon Feb 11 21:22:01 2019

@author: Nick
"""
from matplotlib.figure import Figure
import numpy as np
from matplotlib.backends.backend_qt5agg import (
    FigureCanvas, NavigationToolbar2QT as NavigationToolbar)
from PyQt5.QtWidgets import (QWidget, QApplication, QGridLayout,
                             QTableWidget, QTableWidgetItem,
                             QAbstractItemView, QMenu, QHBoxLayout,
                             QPushButton, QLabel, QFrame, QToolButton,
                             QScrollArea, QLayout, QSizePolicy, QCheckBox,
                             QBoxLayout, QSpacerItem, QButtonGroup)
                             QBoxLayout, QSpacerItem, QMessageBox)
from PyQt5 import (QtGui, QtCore)
import typing
from pwspy.imCube.ImCubeClass import ImCube, FakeCube
from pwspy.imCube.ICMetaDataClass import ICMetaData
from pwspy.utility import PlotNd
from pwspy.imCube.matplotlibwidg import myLasso
import os.path as osp
from matplotlib.widgets import LassoSelector

class LittlePlot(FigureCanvas):
    def __init__(self, data:np.ndarray, cell:ImCube):
        self.fig = Figure()
#        self.data = np.ones((100,100))*np.sin(np.linspace(1,6,num=100))[None,:]
        self.data = data
        self.cell = cell
        ax = self.fig.add_subplot(1,1,1)
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
        self.setLayout(QGridLayout())
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1,1,1)
        self.ax.imshow(data)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.canvas.setFocus()
        self.buttonGroup = QButtonGroup(self)
        self.lassoButton = QPushButton("L")
        self.ellipseButton = QPushButton("O")
        self.lastButton_ = None
        self.buttonGroup.addButton(self.lassoButton,1)
        self.buttonGroup.addButton(self.ellipseButton)
        self.buttonGroup.buttonReleased.connect(self.handleButtons)
        [i.setCheckable(True) for i in self.buttonGroup.buttons()]
        
        self.layout().addWidget(self.lassoButton,0,0,1,1)
        self.layout().addWidget(self.ellipseButton,0,1,1,1)
        self.layout().addWidget(self.canvas,1,0,8,8)
        self.layout().addWidget(NavigationToolbar(self.canvas, self),10,0,8,8)
        self.show()
    def handleButtons(self,button):
        if button != self.lastButton_:
            if button is self.lassoButton:
                self.selector=myLasso(self.ax)
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
            t = '\t'.join([self.horizontalHeaderItem(i).text() for i in range(sel.leftColumn(), sel.rightColumn()+1)]) + '\n'
            for i in range(sel.topRow(), sel.bottomRow()+1):
                for j in range(sel.leftColumn(), sel.rightColumn()+1):
                    if t[-1]!='\n': t += '\t'
                    item = self.item(i,j)
                    t += ' ' if item is None else item.text()                    
                t += '\n'
            QApplication.clipboard().setText(t)
        except Exception as e:
            print("Copy Failed: ",e)
   
class CellTableWidgetItem:
    def __init__(self, cube:ICMetaData, label:str, num:int):
        self.cube = cube
        self.num = num
        self.notesButton = QPushButton("Open")
        self.notesButton.setFixedSize(40,30)
        self.label = QTableWidgetItem(label)
        self.numLabel = QTableWidgetItem(str(num))
        self.notesButton.released.connect(self.editNotes)
        
        self._invalid = False
        
    def editNotes(self):
        self.cube.editNotes()
        
    def setInvalid(self,invalid:bool):
        if invalid:
            self.label.setBackground(QtCore.Qt.red)
        else:
            self.label.setBackground(QtCore.Qt.white)
        self._invalid = invalid
    def isInvalid(self) -> bool :
        return self._invalid
    
class CellTableWidget(QTableWidget):
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.showContextMenu)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        columns = ('Path','Cell#', 'ROIs','Analyses', 'Notes')
        self.setRowCount(0)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.verticalHeader().hide()
        [self.setColumnWidth(i,w) for i,w in zip(range(len(columns)), [60,40,40,50,40])]
        self.cellItems=[]

    def showContextMenu(self, point:QtCore.QPoint):
        menu = QMenu("Context Menu")
        state = not self.selectedCells[0].isInvalid()
        stateString = "Disable Cell(s)" if state else "Enable Cell(s)"
        action = menu.addAction(stateString)
        action.triggered.connect(lambda: self.toggleSelectedCellsInvalid(state))
        menu.exec(self.mapToGlobal(point))
        
    def toggleSelectedCellsInvalid(self, state:bool):
        for i in self.selectedCells:
            i.setInvalid(state)
    
    @property
    def selectedCells(self) -> typing.List[CellTableWidgetItem]:
        '''Returns the rows that have been selected.'''
        rowIndices = [i.row() for i in self.selectedIndexes()[::self.columnCount()]]
        rowIndices.sort()
        return [self.cellItems[i] for i in rowIndices]
    
    @property
    def enabledCells(self) -> typing.List[CellTableWidgetItem]:
        return [i for i in self.cellItems if not i.isInvalid()]
    
    def addCellItem(self, item:CellTableWidgetItem):
        row = len(self.cellItems)
        self.setRowCount(row+1)
        self.setItem(row,0,item.label)
        self.setItem(row, 1, item.numLabel)
        self.setItem(row, 2, QTableWidgetItem(str(3)))#len(cube.getMasks())))
        self.setItem(row, 3, QTableWidgetItem(str(1)))
        self.setCellWidget(row, 4, item.notesButton)
        self.cellItems.append(item)

    
class CollapsibleSection(QWidget):
    stateChanged = QtCore.pyqtSignal(bool)
    def __init__(self, title, animationDuration, parent:QWidget):
        super().__init__(parent)
        self.animationDuration = animationDuration
        self.toggleButton = QCheckBox(title, self)
        headerLine =  QFrame(self);
        self.toggleAnimation = QtCore.QParallelAnimationGroup(self);
        self.contentArea = QScrollArea(self);
        mainLayout = QGridLayout(self);

        self.toggleButton.setCheckable(True);
        self.toggleButton.setChecked(True);

        headerLine.setFrameShape(QFrame.HLine);
        headerLine.setFrameShadow(QFrame.Sunken);
        headerLine.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum);

        self.contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed);
        # start out collapsed
        self.contentArea.setMaximumHeight(0);
        self.contentArea.setMinimumHeight(0);

        # let the entire widget grow and shrink with its content
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"minimumHeight"));
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self, b"maximumHeight"));
        self.toggleAnimation.addAnimation(QtCore.QPropertyAnimation(self.contentArea, b"maximumHeight"));

        mainLayout.setVerticalSpacing(0);
        mainLayout.setContentsMargins(0, 0, 0, 0);

        mainLayout.addWidget(self.toggleButton, 0, 0, 1, 1, QtCore.Qt.AlignLeft)

        mainLayout.addWidget(headerLine, 1, 2, 1, 1)

        mainLayout.addWidget(self.contentArea, 1, 0, 1, 3)

        self.setLayout(mainLayout);
        self.setLayout = self.setLayout_

        self.toggleButton.toggled.connect(
                lambda checked: 
                    [#self.toggleButton.setArrowType(QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow),
                    self.toggleAnimation.setDirection(QtCore.QAbstractAnimation.Forward if not checked else QtCore.QAbstractAnimation.Backward),
                    self.toggleAnimation.start()])
        self.toggleAnimation.finished.connect(lambda: self.stateChanged.emit(self.toggleButton.isChecked()))

    def setLayout_(self, contentLayout:QLayout):
        oldLayout = self.contentArea.layout()
        del oldLayout
        self.contentArea.setLayout(contentLayout)
        collapsedHeight = self.sizeHint().height() - self.contentArea.maximumHeight();
        contentHeight = contentLayout.sizeHint().height();
    
        for i in range(self.toggleAnimation.animationCount()-1):
            SectionAnimation = self.toggleAnimation.animationAt(i)
            SectionAnimation.setDuration(self.animationDuration)
            SectionAnimation.setStartValue(collapsedHeight)
            SectionAnimation.setEndValue(collapsedHeight + contentHeight)
    
        contentAnimation = self.toggleAnimation.animationAt(self.toggleAnimation.animationCount() - 1)
        contentAnimation.setDuration(self.animationDuration);
        contentAnimation.setStartValue(0);
        contentAnimation.setEndValue(contentHeight);
        
class AspectRatioWidget(QWidget):
    def __init__(self, widget:QWidget, aspect:float, parent:QWidget = None):
        super().__init__(parent)
        self.aspect = aspect
        self.layout = QBoxLayout(QBoxLayout.LeftToRight, self)
        self.widget = widget
        # add spacer, then your widget, then spacer
        self.layout.addItem(QSpacerItem(0, 0));
        self.layout.addWidget(widget);
        self.layout.addItem(QSpacerItem(0, 0));

    def resizeEvent(self, event:QtGui.QResizeEvent):
        thisAspectRatio = event.size().width() / event.size().height()
    
        if (thisAspectRatio > self.aspect): # too wide
            self.layout.setDirection(QBoxLayout.LeftToRight);
            widgetStretch = self.height() * self.aspect; # i.e., my width
            outerStretch = (self.width() - widgetStretch) / 2 + 0.5;
        else: #too tall
            self.layout.setDirection(QBoxLayout.TopToBottom);
            widgetStretch = self.width() * (1/self.aspect); # i.e., my height
            outerStretch = (self.height() - widgetStretch) / 2 + 0.5;
    
        self.layout.setStretch(0, outerStretch);
        self.layout.setStretch(1, widgetStretch);
        self.layout.setStretch(2, outerStretch);
    
    def setAspect(self, aspect:float):
        self.aspect = aspect