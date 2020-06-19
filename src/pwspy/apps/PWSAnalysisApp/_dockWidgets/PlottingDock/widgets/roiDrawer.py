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

import enum
import queue
from time import time
from typing import List, Tuple, Optional

import numpy as np
from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QMetaObject, pyqtSlot
from PyQt5.QtWidgets import QWidget, QGridLayout, QButtonGroup, QPushButton, QDialog, QSpinBox, QLabel, \
    QMessageBox, QMenu, QAction, QApplication

from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateAnalysisResults
from pwspy.dataTypes import AcqDir
from matplotlib import patches
import os
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.analysisViewer import AnalysisViewer
from pwspy.utility.matplotlibWidgets._selectorWidgets.FullImPaintSelector import FullImPaintSelector
from pwspy.dataTypes import Roi
from pwspy.utility.matplotlibWidgets import AdjustableSelector, LassoSelector, EllipseSelector, RegionalPaintSelector, PolygonInteractor
import multiprocessing as mp


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

class QueueCheckerThread(QObject):
    roiFinished = pyqtSignal(Roi)
    roiNeedsOverwrite = pyqtSignal(Roi)

    def __init__(self, resultsQ: mp.Queue):
        super().__init__()
        self._q = resultsQ

    @pyqtSlot()
    def doWork(self):
        print(f"Running doWork on {QThread.currentThread().objectName()}, {QThread.currentThread()}")
        while True:
            if QThread.currentThread().isInterruptionRequested():
                break
            try:
                resultCode, roi = self._q.get(True, .5)
            except queue.Empty:
                continue
            if resultCode is Cmd.SUCESS:
                self.roiFinished.emit(roi)
            elif resultCode is Cmd.NEEDSOVERWRITE:
                self.roiNeedsOverwrite.emit(roi)
            elif resultCode is Cmd.QUIT:
                break
            elif isinstance(resultCode, Exception):
                raise resultCode
            else:
                raise ValueError("HUH!")

class Cmd(enum.Enum):
    SUCESS = enum.auto()
    NEEDSOVERWRITE = enum.auto()
    QUIT = enum.auto()


class RoiSaverProcess(mp.Process):
    """This class handles the actual saving of the roi and everything that can be performed in a separate process."""
    def __init__(self):
        super().__init__()
        self._q = mp.Queue()
        self._resultQ = mp.Queue()

    def run(self):
        """This is what gets run in the other process when `start` is called."""
        try:
            while True:
                try:
                    item = self._q.get(True, 0.5)
                except queue.Empty:
                    continue
                if item is Cmd.QUIT:
                    self._resultQ.put((item, None), True, 0.5)
                    break
                name, num, verts, datashape, acq = item  # If we got this far then item must be commands for a new saving.
                roi = Roi.fromVerts(name, num, verts, datashape)
                try:
                    acq.saveRoi(roi)
                    self._resultQ.put((Cmd.SUCESS, roi), True, 0.5)
                except OSError:
                    self._resultQ.put((Cmd.NEEDSOVERWRITE, roi), True, 0.5)
        except Exception as e:
            self._resultQ.put((e, None), True, 0.5)

    def requestClose(self):
        self._q.put(Cmd.QUIT, True, 0.5)

    def saveNewRoi(self, name: str, num: int, verts, datashape, acq: AcqDir):
        """Call this from the main process to start saving in the saver process."""
        self._q.put((name, num, verts, datashape, acq), True, 0.5)

    def getResultsQ(self):
        return self._resultQ

class RoiSaverController(QObject):
    """Instantiating this class begins the process of saving a ROI. This class handles the GUI related stuff in the main thread."""
    def open(self):
        self.worker.start()
        self.thread.start()

    def close(self):
        self.worker.requestClose()
        self.thread.requestInterruption()
        self.thread.wait(1000)
        self.worker.join(1) #Wait up to one second for the process to finish cleanly.
        self.worker.close()

    def saveNewRoi(self, name: str, num: int, verts, datashape, acq: AcqDir):
        self.placeHolderPoly = patches.Polygon(verts, facecolor=(0, .5, 0.5, 0.4)) #this is a temporary polygon display until the ROI file is actually ready to be read.
        self.anViewer.ax.add_patch(self.placeHolderPoly)
        self.worker.saveNewRoi(name, num, verts, datashape, acq)
        self.anViewer.canvas.draw_idle()

    def __init__(self, anViewer, parent: QWidget):
        """This initializer starts a separate thread and runs RoiSaverWorker.doWork on that thread. GUI related work is linked to the appropriate
        signals from the other thread. This multithreaded approach turns out to be mostly pointless. Because of pythons GIL the roid drawing still becomes
        temporarily frozen while the ROI is saved. It seems the only way to make this faster is to optimize the saving operation."""
        super().__init__(parent)
        self.anViewer = anViewer
        self.worker = RoiSaverProcess()
        self.thread = QThread()
        self.qChecker = QueueCheckerThread(self.worker.getResultsQ())
        self.thread.setObjectName('QueueCheckerThread')
        self.qChecker.moveToThread(self.thread)
        self.thread.started.connect(self.qChecker.doWork)
        self.qChecker.roiFinished.connect(self.drawSavedRoi)
        self.qChecker.roiNeedsOverwrite.connect(self.overWriteRoi)
        # QThread.currentThread().setObjectName("MainThread")
        # print(f"This thread {QThread.currentThread().objectName()}, {QThread.currentThread()}")
        # print(f"Created thread {self.thread.objectName()}, {self.thread}")


    def overWriteRoi(self, roi: Roi):
        """If the worker raised an `OSError` then we need to ask the user if they want to overwrite. This must be done in the main thread."""
        ans = QMessageBox.question(self.anViewer, 'Overwrite?', f"Roi {roi.name}:{roi.number} already exists. Overwrite?")
        if ans == QMessageBox.Yes:
            self.acq.saveRoi(roi, overwrite=True)
            self.anViewer.showRois() #Refresh all rois since we just deleted one as well.
            self.roiIsSaved()
        self.finish()

    def drawSavedRoi(self, roi: Roi):
        """The worker successfully save the roi, now display it."""
        self.anViewer.addRoi(roi)
        self.roiIsSaved()
        self.finish()

    def roiIsSaved(self):
        """Either way, once a  new roi has been saved we want to do this."""
        QApplication.instance().window.cellSelector.refreshCellItems()  # Refresh the cell selection table.

    def finish(self):
        """Even if the roi wasn't ultimately saved we want to do this."""
        self.placeHolderPoly.remove()
        self.anViewer.canvas.draw_idle()
