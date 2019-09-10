from __future__ import annotations
from typing import List, Tuple, Optional

import numpy as np
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QGridLayout, QButtonGroup, QPushButton, QDialog, QSpinBox, QLabel, \
    QMessageBox
from pwspy.dataTypes import AcqDir
from matplotlib import patches
import os
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.analysisViewer import AnalysisViewer
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.bigPlot import BigPlot
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ICMetaData
from pwspy.dataTypes import Roi
from pwspy.utility.matplotlibwidg import AdjustableSelector, MyLasso, MyEllipse, MyPaint, PolygonInteractor


class RoiDrawer(QWidget):
    def __init__(self, metadatas: List[Tuple[AcqDir, Optional[PWSAnalysisResults]]], parent=None):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        self.setWindowTitle("Roi Drawer 3000")
        self.metadatas = metadatas
        layout = QGridLayout()
        self.mdIndex = 0
        self.newRoiDlg = NewRoiDlg(self)
        self.anViewer = AnalysisViewer(metadatas[self.mdIndex][0], metadatas[self.mdIndex][1], 'title')
        self.buttonGroup = QButtonGroup(self)
        self.noneButton = QPushButton("Inspect")
        self.lassoButton = QPushButton("Lasso")
        self.lassoButton.setToolTip(MyLasso.getHelpText())
        self.ellipseButton = QPushButton("Ellipse")
        self.ellipseButton.setToolTip(MyEllipse.getHelpText())
        self.paintButton = QPushButton("Paint")
        self.paintButton.setToolTip(MyPaint.getHelpText())
        self.lastButton_ = None
        self.buttonGroup.addButton(self.noneButton)
        self.buttonGroup.addButton(self.lassoButton)
        self.buttonGroup.addButton(self.ellipseButton)
        self.buttonGroup.addButton(self.paintButton)
        self.buttonGroup.buttonReleased.connect(self.handleButtons)
        [i.setCheckable(True) for i in self.buttonGroup.buttons()]
        self.noneButton.setChecked(True)
        self.adjustButton = QPushButton("Adj")
        self.adjustButton.setToolTip(PolygonInteractor.getHelpText())
        self.adjustButton.setCheckable(True)
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
        self.selector: AdjustableSelector = AdjustableSelector(self.anViewer.plotWidg.ax, self.anViewer.plotWidg.im, MyLasso, onfinished=self.finalizeRoi)
        self.show()

    def finalizeRoi(self, verts: np.ndarray):
        poly = patches.Polygon(verts, facecolor=(0, .5, 0.5, 0.4))
        shape = self.anViewer.plotWidg.data.shape
        self.anViewer.plotWidg.ax.add_patch(poly)
        self.anViewer.plotWidg.canvas.draw_idle()
        roiName = self.anViewer.plotWidg.roiFilter.currentText()
        if roiName == '':
            QMessageBox.information(self, 'Wait', 'Please type an ROI name into the box at the bottom of the screen.')
            self.selector.setActive(True)
            return
        self.newRoiDlg.show()
        self.newRoiDlg.exec()
        poly.remove()
        if self.newRoiDlg.result() == QDialog.Accepted:
            r = Roi.fromVerts(roiName, self.newRoiDlg.number, verts=np.array(verts), dataShape=shape)
            md = self.metadatas[self.mdIndex][0]
            try:
                md.saveRoi(r)
                self.anViewer.plotWidg.addRoi(r)
            except OSError: #We must already have this roi saved
                ans = QMessageBox.question(self, 'Overwrite?', f"Roi {r.name}:{r.number} already exists. Overwrite?")
                if ans == QMessageBox.Yes:
                    md.saveRoi(r, overwrite=True)
                    self.anViewer.plotWidg.showRois() #Refresh all rois since we just deleted one as well.
        self.anViewer.plotWidg.canvas.draw_idle()
        self.selector.setActive(True)  # Start the next roi.

    def handleButtons(self, button):
        if button != self.lastButton_:
            if button is self.lassoButton:
                self.selector.setSelector(MyLasso)
                self.selector.setActive(True)
                self.anViewer.plotWidg.enableHoverAnnotation(False)
                self.adjustButton.setEnabled(True)
            elif button is self.ellipseButton:
                self.selector.setSelector(MyEllipse)
                self.selector.setActive(True)
                self.anViewer.plotWidg.enableHoverAnnotation(False)
                self.adjustButton.setEnabled(True)
            elif button is self.paintButton:
                self.selector.setSelector(MyPaint)
                self.selector.setActive(True)
                self.anViewer.plotWidg.enableHoverAnnotation(False)
                self.adjustButton.setEnabled(True)
            elif button is self.noneButton:
                self.selector.setActive(False)
                self.anViewer.plotWidg.enableHoverAnnotation(True)
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
        currRoi = self.anViewer.plotWidg.roiFilter.currentText() #Since the next cell we look at will likely not have rois of the current name we want to manually force the ROI name to stay the same.
        md, analysis = self.metadatas[self.mdIndex]
        self.anViewer.setMetadata(md, analysis=analysis)
        self.anViewer.plotWidg.roiFilter.setEditText(currRoi)
        self.setWindowTitle(f"Roi Drawer - {os.path.split(md.filePath)[-1]}")

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
        if len(self.parent.anViewer.plotWidg._rois) > 0:
            rois, ims, polys = zip(*self.parent.anViewer.plotWidg._rois)
            newNum = max([r.number for r in rois]) + 1 #Set the box 1 number abox the maximum found
            self.numBox.setValue(newNum)
        else:
            self.numBox.setValue(0) #start at 0
        super().show()
