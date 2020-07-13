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

from __future__ import annotations

from typing import List, Tuple, Optional

import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtWidgets import QWidget, QGridLayout, QButtonGroup, QPushButton, QDialog, QSpinBox, QLabel, \
    QMessageBox, QMenu, QAction

from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.roiDrawerProcess import RoiSaverController
from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateAnalysisResults
from pwspy.dataTypes import AcqDir
import os
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.analysisViewer import AnalysisViewer
from pwspy.utility.matplotlibWidgets._selectorWidgets.FullImPaintSelector import FullImPaintSelector
from pwspy.utility.matplotlibWidgets import AdjustableSelector, LassoSelector, EllipseSelector, RegionalPaintSelector, PolygonInteractor


class RoiDrawer(QWidget):
    def __init__(self, metadatas: List[Tuple[AcqDir, Optional[ConglomerateAnalysisResults]]], parent=None):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        self.setWindowTitle("Roi Drawer 3000")
        self.metadatas = metadatas

        layout = QGridLayout()

        self.mdIndex = 0
        self.anViewer = AnalysisViewer(metadatas[self.mdIndex][0], metadatas[self.mdIndex][1], 'title')
        self.saver = RoiSaverController(self.anViewer, self)
        self.saver.open()  # This opens a new thread and a process, make sure to call close when the widget is closed.

        self.newRoiDlg = NewRoiDlg(self)
        self.buttonGroup = QButtonGroup(self)
        self.noneButton = QPushButton("Inspect")
        self.lassoButton = QPushButton("Lasso")
        self.lassoButton.setToolTip(LassoSelector.getHelpText())
        self.ellipseButton = QPushButton("Ellipse")
        self.ellipseButton.setToolTip(EllipseSelector.getHelpText())
        self.paintButton = QPushButton("Paint")
        self.paintButton.setToolTip(RegionalPaintSelector.getHelpText())
        self.lastButton_ = None
        self.buttonGroup.addButton(self.noneButton)
        self.buttonGroup.addButton(self.lassoButton)
        self.buttonGroup.addButton(self.ellipseButton)
        self.buttonGroup.addButton(self.paintButton)
        self.buttonGroup.buttonReleased.connect(self.handleButtons)
        [i.setCheckable(True) for i in self.buttonGroup.buttons()]
        self.noneButton.setChecked(True) #This doesn't seem totrigger handle buttons. we'll do that at the end of the constructor
        self.adjustButton = QPushButton("Tune")
        self.adjustButton.setToolTip(PolygonInteractor.getHelpText())
        self.adjustButton.setCheckable(True)
        self.adjustButton.setMaximumWidth(50)
        self.adjustButton.toggled.connect(self.handleAdjustButton)
        self.previousButton = QPushButton('←')
        self.nextButton = QPushButton('→')
        self.previousButton.released.connect(self.showPreviousCell)
        self.nextButton.released.connect(self.showNextCell)

        layout.addWidget(self.noneButton, 0, 0, 1, 1)
        layout.addWidget(self.lassoButton, 0, 1, 1, 1)
        layout.addWidget(self.ellipseButton, 0, 2, 1, 1)
        layout.addWidget(self.paintButton, 0, 3, 1, 1)
        layout.addWidget(self.adjustButton, 0, 4, 1, 1)
        layout.addWidget(self.previousButton, 0, 6, 1, 1)
        layout.addWidget(self.nextButton, 0, 7, 1, 1)
        layout.addWidget(self.anViewer, 1, 0, 8, 8)
        self.setLayout(layout)
        self.selector: AdjustableSelector = AdjustableSelector(self.anViewer.ax, self.anViewer.im, LassoSelector, onfinished=self.finalizeRoi)
        self.handleButtons(self.noneButton) #Helps initialize state
        self.show()

    def finalizeRoi(self, verts: np.ndarray):
        roiName = self.anViewer.roiFilter.currentText()
        if roiName == '':
            QMessageBox.information(self, 'Wait', 'Please type an ROI name into the box at the top of the screen.')
            self.selector.setActive(True)
            return
        shape = self.anViewer.data.shape
        self.newRoiDlg.show()
        self.newRoiDlg.exec()
        if self.newRoiDlg.result() == QDialog.Accepted:
            md = self.metadatas[self.mdIndex][0]
            self.saver.saveNewRoi(roiName, self.newRoiDlg.number, np.array(verts), shape, md)
        self.selector.setActive(True)  # Start the next roi.

    def handleButtons(self, button):
        if button is self.lassoButton and self.lastButton_ is not button:
            self.selector.setSelector(LassoSelector)
            self.selector.setActive(True)
            self.anViewer.enableHoverAnnotation(False)
            self.adjustButton.setEnabled(True)
        elif button is self.ellipseButton and self.lastButton_ is not button:
            self.selector.setSelector(EllipseSelector)
            self.selector.setActive(True)
            self.anViewer.enableHoverAnnotation(False)
            self.adjustButton.setEnabled(True)
        elif button is self.paintButton:
            def setSelector(sel):
                self.selector.setSelector(sel)
                self.selector.setActive(True)
                self.anViewer.enableHoverAnnotation(False)
                self.adjustButton.setEnabled(True)

            menu = QMenu(self)
            regionalAction = QAction("Regional")
            regionalAction.triggered.connect(lambda: setSelector(RegionalPaintSelector))
            menu.addAction(regionalAction)
            fullAction = QAction("Full Image")
            fullAction.triggered.connect(lambda: setSelector(FullImPaintSelector))
            menu.addAction(fullAction)
            menu.exec(self.mapToGlobal(self.paintButton.pos()))

        elif button is self.noneButton and self.lastButton_ is not button:
            if self.selector is not None:
                self.selector.setActive(False)
            self.anViewer.enableHoverAnnotation(True)
            self.adjustButton.setEnabled(False)
        self.lastButton_ = button

    def handleAdjustButton(self, checkstate: bool):
        if self.selector is not None:
            self.selector.adjustable = checkstate

    def showNextCell(self):
        self.mdIndex += 1
        if self.mdIndex >= len(self.metadatas):
            self.mdIndex = 0
        self._updateDisplayedCell()

    def showPreviousCell(self):
        self.mdIndex -= 1
        if self.mdIndex < 0:
            self.mdIndex = len(self.metadatas) - 1
        self._updateDisplayedCell()

    def _updateDisplayedCell(self):
        currRoi = self.anViewer.roiFilter.currentText() #Since the next cell we look at will likely not have rois of the current name we want to manually force the ROI name to stay the same.
        md, analysis = self.metadatas[self.mdIndex]
        self.anViewer.setMetadata(md, analysis=analysis)
        self.anViewer.roiFilter.setEditText(currRoi) #manually force the ROI name to stay the same.
        self.selector.reset() #Make sure to get rid of all rois
        self.setWindowTitle(f"Roi Drawer - {os.path.split(md.filePath)[-1]}")

    def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
        self.selector.setActive(False) #This cleans up remaining resources of the selector widgets.
        self.saver.close()  # should close the saver process and threads.
        super().closeEvent(a0)


class NewRoiDlg(QDialog):
    def __init__(self, parent: RoiDrawer):
        super().__init__(parent=parent)#, flags=QtCore.Qt.FramelessWindowHint)
        self.parent = parent
        self.setModal(True)

        self.number = None

        l = QGridLayout()
        self.numBox = QSpinBox()
        self.numBox.setMaximum(100000)
        self.numBox.setMinimum(0)
        self.okButton = QPushButton("Ok")
        self.okButton.released.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.released.connect(self.reject)
        l.addWidget(QLabel("#"), 0, 0, 1, 1, alignment=QtCore.Qt.AlignRight)
        l.addWidget(self.numBox, 0, 1, 1, 1)
        l.addWidget(self.okButton, 1, 0, 1, 1)
        l.addWidget(self.cancelButton, 1, 1, 1, 1)
        self.setLayout(l)

    def accept(self) -> None:
        self.number = self.numBox.value()
        self.numBox.setValue(self.numBox.value()+1)  # Increment the value.
        super().accept()

    def reject(self) -> None:
        self.number = None
        super().reject()

    def show(self) -> None:
        if len(self.parent.anViewer.rois) > 0:
            rois, ims, polys = zip(*self.parent.anViewer.rois)
            newNum = max([r.number for r in rois]) + 1 #Set the box 1 number abox the maximum found
            self.numBox.setValue(newNum)
        else:
            self.numBox.setValue(0) #start at 0
        super().show()


