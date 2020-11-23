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

import logging
import os
import re
import typing
from dataclasses import dataclass

import matplotlib
from shapely.geometry import Polygon as shapelyPolygon
from matplotlib.backend_bases import KeyEvent, MouseEvent
from matplotlib.image import AxesImage
from matplotlib.patches import  Polygon
import numpy as np
from PyQt5.QtGui import QCursor, QValidator
from PyQt5.QtWidgets import QMenu, QAction, QComboBox, QLabel, QPushButton, QHBoxLayout, QDialog, QWidget, QSlider, QGridLayout, QSpinBox, QDoubleSpinBox, \
    QMessageBox, QVBoxLayout
from PyQt5 import QtCore
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.bigPlot import BigPlot
from pwspy.dataTypes import Roi, AcqDir
from pwspy.utility.matplotlibWidgets import PolygonModifier, AxManager
from pwspy.utility.matplotlibWidgets._modifierWidgets.movingModifier import MovingModifier
from pwspy.utility.plotting.roiColor import roiColor

@dataclass
class RoiParams:
    roi: Roi
    overlay: AxesImage
    polygon: Polygon
    selected: bool


class RoiPlot(QWidget):
    """Adds handling for ROIs to the BigPlot class."""
    def __init__(self, acqDir: AcqDir, data: np.ndarray, parent=None, flags: QtCore.Qt.WindowFlags = None):
        if flags is not None:
            super().__init__(parent, flags=flags)
        else:
            super().__init__(parent=parent)
        self._plotWidget = BigPlot(data, self)
        self.data = self._plotWidget.data #TODO These variables are used by other widgets, leftover from when we used inheritance rather than encapsulation, it would be good to get rid of them.
        self.im = self._plotWidget.im
        self.ax = self._plotWidget.ax
        self.canvas = self._plotWidget.canvas
        self.rois: typing.List[RoiParams] = []  # This list hold information about the ROIs that are currently displayed.
        self.axManager = AxManager(self._plotWidget.ax)  # This object manages redrawing of the matplotlib axes for us.

        self.roiFilter = QComboBox(self)
        self.roiFilter.setEditable(True)
        self.roiFilter.setValidator(WhiteSpaceValidator())

        self.exportButton = QPushButton("Export")
        self.exportButton.released.connect(self._exportAction)

        layout = QVBoxLayout()
        l = QHBoxLayout()
        l.addWidget(QLabel("Roi"), alignment=QtCore.Qt.AlignRight)
        l.addWidget(self.roiFilter)
        l.addWidget(self.exportButton)
        layout.addLayout(l)
        layout.addWidget(self._plotWidget)
        self.setLayout(layout)

        self.setRoiPlotMetadata(acqDir)

        self.annot = self._plotWidget.ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))

        self._toggleCids = None
        self.enableHoverAnnotation(True)


    def setRoiPlotMetadata(self, metadata: AcqDir):
        """Refresh the ROIs based on a new metadata. Also needs to be provided with the data for the image to display."""
        self.metadata = metadata
        self.clearRois()
        currentSel = self.roiFilter.currentText()
        # updateFilter
        try:
            self.roiFilter.currentIndexChanged.disconnect() # Without this line the roiFilter.clear() line is very slow.
        except:
            pass #if the signal hasn't yet been connected we'll get an error. ignore it.
        self.roiFilter.clear()
        self.roiFilter.addItem(' ')
        self.roiFilter.addItem('.*')
        rois = self.metadata.getRois()
        roiNames = set(list(zip(*rois))[0]) if len(rois) > 0 else []
        self.roiFilter.addItems(roiNames)
        self.roiFilter.currentIndexChanged.connect(self.showRois)
        for i in range(self.roiFilter.count()):
            if currentSel == self.roiFilter.itemText(i):
                self.roiFilter.setCurrentIndex(i)
                break

    def _hoverCallback(self, event):  # Show an annotation about the ROI when the mouse hovers over it.
        def update_annot(roi, poly):
            self.annot.xy = poly.xy.mean(axis=0)  # Set the location to the center of the polygon.
            text = f"{roi.name}, {roi.number}"
            if self.metadata.pws:  # A day may come where fluorescence is not taken on the same camera as pws, in this case we will have multiple pixel sizes and ROI handling will need an update. for now just assume we'll use PWS pixel size
                if self.metadata.pws.pixelSizeUm: # For some systems (nanocytomics) this is None
                    text += f"\n{self.metadata.pws.pixelSizeUm ** 2 * np.sum(roi.mask):.2f} $μm^2$"
            self.annot.set_text(text)
            self.annot.get_bbox_patch().set_alpha(0.4)

        vis = self.annot.get_visible()
        if event.inaxes == self._plotWidget.ax:
            for params in self.rois:
                contained, _ = params.polygon.contains(event)
                if contained:
                    if not vis:
                        update_annot(params.roi, params.polygon)
                        self.annot.set_visible(True)
                        self._plotWidget.canvas.draw_idle()
                    return
            if vis:  # If we got here then no hover actions were found.
                self.annot.set_visible(False)
                self._plotWidget.canvas.draw_idle()

    def setRoiSelected(self, roi: Roi, selected: bool):
        param = [param for param in self.rois if roi is param.roi][0]
        param.selected = selected
        if selected:
            param.polygon.set_edgecolor((0, 1, 1, 0.9))  # Highlight selected rois.
            param.polygon.set_linewidth(2)
        else:
            param.polygon.set_edgecolor((0, 1, 0, 0.9))
            param.polygon.set_linewidth(1)

    def _keyPressCallback(self, event: KeyEvent):
        pass

    def _mouseClickCallback(self, event: MouseEvent):
        # Determine if a ROI was clicked on
        _ = [param for param in self.rois if param.polygon.contains(event)[0]]
        if len(_) > 0:
            selectedROIParam = _[0]  # There should have only been one roi clicked on. select the first one from the list (hopefully only one there anyway)
        else:
            selectedROIParam = None #No Roi was clicked

        if event.button == 1 and selectedROIParam is not None: #Left click
            self.setRoiSelected(selectedROIParam.roi, not selectedROIParam.selected)
            self._plotWidget.canvas.draw_idle()
        if event.button == 3:  # "3" is the right button
            #Actions that can happen even if no ROI was clicked on.
            def deleteFunc():
                for param in self.rois:
                    if param.selected:
                        param.roi.deleteRoi(os.path.split(param.roi.filePath)[0], param.roi.name, param.roi.number)
                self.showRois()

            def moveFunc():
                coordSet = []
                selectedROIParams = []
                for param in self.rois:
                    if param.selected:
                        selectedROIParams.append(param)
                        coordSet.append(param.roi.verts)

                def done(vertsSet, handles):
                    for param, verts in zip(selectedROIParams, vertsSet):
                        newRoi = Roi.fromVerts(param.roi.name, param.roi.number, np.array(verts),
                                               param.roi.mask.shape)
                        newRoi.toHDF(self.metadata.filePath, overwrite=True)
                    self._polyWidg.set_active(False)
                    self._polyWidg.set_visible(False)
                    self.showRois()
                    self.enableHoverAnnotation(True)

                def cancelled():
                    self.enableHoverAnnotation(True)

                self.enableHoverAnnotation(False) #This should be reenabled when the widget is finished or cancelled.
                self._polyWidg = MovingModifier(self.axManager, onselect=done, onCancelled=cancelled)
                self._polyWidg.set_active(True)
                self._polyWidg.initialize(coordSet)

            def selectAllFunc():
                sel = not any([param.selected for param in self.rois])  # Determine whether to selece or deselect all
                for param in self.rois:
                    self.setRoiSelected(param.roi, sel)
                self._plotWidget.canvas.draw_idle()

            popMenu = QMenu(self)
            deleteAction = popMenu.addAction("Delete Selected ROIs", deleteFunc)
            moveAction = popMenu.addAction("Move Selected ROIs", moveFunc)
            selectAllAction = popMenu.addAction("De/Select All", selectAllFunc)

            if not any([roiParam.selected for roiParam in self.rois]): # If no rois are selected then some actions can't be performed
                deleteAction.setEnabled(False)
                moveAction.setEnabled(False)

            moveAction.setToolTip(MovingModifier.getHelpText())
            popMenu.setToolTipsVisible(True)

            if selectedROIParam is not None:
                #Actions that require that a ROI was clicked on.
                def editFunc():
                    # extract handle points from the polygon
                    poly = shapelyPolygon(selectedROIParam.roi.verts)
                    poly = poly.buffer(0)
                    poly = poly.simplify(poly.length ** .5 / 5, preserve_topology=False)
                    handles = poly.exterior.coords

                    def done(verts, handles):
                        verts = verts[0]
                        newRoi = Roi.fromVerts(selectedROIParam.roi.name, selectedROIParam.roi.number, np.array(verts), selectedROIParam.roi.mask.shape)
                        newRoi.toHDF(self.metadata.filePath, overwrite=True)
                        self._polyWidg.set_active(False)
                        self._polyWidg.set_visible(False)
                        self.enableHoverAnnotation(True)
                        self.showRois()

                    def cancelled():
                        self.enableHoverAnnotation(True)

                    self._polyWidg = PolygonModifier(self.axManager, onselect=done, onCancelled=cancelled)
                    self._polyWidg.set_active(True)
                    self.enableHoverAnnotation(False)
                    self._polyWidg.initialize([handles])

                popMenu.addSeparator()
                popMenu.addAction("Modify", editFunc)

            cursor = QCursor()
            popMenu.popup(cursor.pos())

    def enableHoverAnnotation(self, enable: bool):
        if enable:
            self._toggleCids = [self._plotWidget.canvas.mpl_connect('motion_notify_event', self._hoverCallback),
                                self._plotWidget.canvas.mpl_connect('button_press_event', self._mouseClickCallback),
                                self._plotWidget.canvas.mpl_connect('key_press_event', self._keyPressCallback)]
        else:
            if self._toggleCids:
                [self._plotWidget.canvas.mpl_disconnect(cid) for cid in self._toggleCids]

    def showRois(self):
        pattern = self.roiFilter.currentText()
        self.clearRois()
        for name, num, fformat in self.metadata.getRois():
            if re.fullmatch(pattern, name):
                try:
                    self.addRoi(self.metadata.loadRoi(name, num, fformat))
                except Exception as e:
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to load Roi with name: {name}, number: {num}, format: {fformat.name}")
                    logger.exception(e)
        self._plotWidget.canvas.draw_idle()

    def clearRois(self):
        for param in self.rois:
            if param.overlay is not None:
                param.overlay.remove()
            param.polygon.remove()
        self.rois = []

    def addRoi(self, roi: Roi):
        if roi.verts is not None:
            poly = roi.getBoundingPolygon()
            poly.set_picker(0)  # allow the polygon to trigger a pickevent
            self._plotWidget.ax.add_patch(poly)
            self.rois.append(RoiParams(roi, None, poly, False))
        else:  # In the case of old ROI files where the vertices of the outline are not available we have to back-calculate the polygon which does not look good. We make this polygon invisible so it is only used for click detection. we then display an image of the binary mask array.
            overlay = roi.getImage(self._plotWidget.ax) # an image showing the exact shape of the ROI
            poly = roi.getBoundingPolygon() # A polygon used for mouse event handling
            poly.set_visible(False)#poly.set_facecolor((0,0,0,0)) # Make polygon invisible
            poly.set_picker(0) # allow the polygon to trigger a pickevent
            self._plotWidget.ax.add_patch(poly)
            self.rois.append(RoiParams(roi, overlay, poly, False))

    def _exportAction(self):
        def showSinCityDlg():
            dlg = SinCityDlg(self, self)
            dlg.show()
        menu = QMenu("Export Menu")
        act = QAction("Colored Nuclei")
        act.triggered.connect(showSinCityDlg)
        menu.addAction(act)
        menu.exec(self.mapToGlobal(self.exportButton.pos()))

    def setImageData(self, data: np.ndarray):
        self._plotWidget.setImageData(data)


class WhiteSpaceValidator(QValidator):
    stateChanged = QtCore.pyqtSignal(QValidator.State)

    def __init__(self):
        super().__init__()
        self.state = QValidator.Acceptable

    def validate(self, inp: str, pos: int):
        oldState = self.state
        inp = self.fixup(inp)
        self.state = QValidator.Acceptable
        if self.state != oldState: self.stateChanged.emit(self.state)
        return self.state, inp, pos

    def fixup(self, a0: str) -> str:
        return a0.strip()


class SinCityDlg(QDialog):
    def __init__(self, parentRoiPlot: RoiPlot, parent: QWidget = None):
        super().__init__(parent=parent)
        # self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)  # Get rid of the close button. this is handled by the selector widget active status
        self.setWindowTitle("Sin City Image Export")
        self.setModal(False)

        self.parentRoiPlot = parentRoiPlot
        self.cachedImage = None

        self.fig, self.ax = matplotlib.pyplot.subplots()
        c = FigureCanvasQTAgg(self.fig)
        self.plotWidg = QWidget(self)
        self.plotWidg.setLayout(QVBoxLayout())
        self.plotWidg.layout().addWidget(c)
        self.plotWidg.layout().addWidget(NavigationToolbar2QT(c, self))

        self.ax.xaxis.set_visible(False)
        self.ax.yaxis.set_visible(False)
        self.im = self.ax.imshow(self.parentRoiPlot.data)

        self._paintDebounce = QtCore.QTimer()  # This timer prevents the selectionChanged signal from firing too rapidly.
        self._paintDebounce.setInterval(200)
        self._paintDebounce.setSingleShot(True)
        self._paintDebounce.timeout.connect(self.paint)

        self.vmin = QDoubleSpinBox(self)
        self.vmin.setValue(0)
        self.vmin.setDecimals(3)
        self.vmin.setMaximum(10000)
        self.vmin.setSingleStep(0.001)
        def vminChanged(val):
            self.stale = True
            self._paintDebounce.start()
        self.vmin.valueChanged.connect(vminChanged)

        self.vmax = QDoubleSpinBox(self)
        self.vmax.setValue(.1)
        self.vmax.setDecimals(3)
        self.vmax.setMaximum(10000)
        self.vmax.setSingleStep(0.001)
        def vmaxChanged(val):
            self.stale = True
            self._paintDebounce.start()
        self.vmax.valueChanged.connect(vmaxChanged)

        self.scaleBg = QDoubleSpinBox(self)
        self.scaleBg.setValue(.33)
        self.scaleBg.setMinimum(0)
        self.scaleBg.setDecimals(2)
        self.scaleBg.setMaximum(3)
        self.scaleBg.setSingleStep(0.01)
        def scaleBgChanged(val):
            self.stale = True
            self._paintDebounce.start()
        self.scaleBg.valueChanged.connect(scaleBgChanged)

        self.hue = QDoubleSpinBox(self)
        self.hue.setMinimum(0)
        self.hue.setMaximum(1)
        self.hue.setValue(0)
        self.hue.setSingleStep(0.05)
        def hueRangeChanged(val):
            self.stale = True
            self._paintDebounce.start()
        self.hue.valueChanged.connect(hueRangeChanged)

        self.exp = QDoubleSpinBox(self)
        self.exp.setMinimum(0.5)
        self.exp.setMaximum(3)
        self.exp.setValue(1)
        self.exp.setSingleStep(0.05)
        def expRangeChanged(val):
            self.stale = True
            self._paintDebounce.start()
        self.exp.valueChanged.connect(expRangeChanged)


        self.scaleBar = QSpinBox(self)
        self.scaleBar.setValue(0)
        self.scaleBar.setMaximum(10000)
        def scaleBarChanged(val):
            self.stale = True
            self._paintDebounce.start()
        self.scaleBar.valueChanged.connect(scaleBarChanged)

        self.refreshButton = QPushButton("Refresh", self)

        def refreshAction():
            self.stale = True  # Force a full refresh
            self.paint()

        self.refreshButton.released.connect(refreshAction)

        l = QGridLayout()
        l.addWidget(QLabel("Minimum Value", self), 0, 0)
        l.addWidget(self.vmin, 0, 1)
        l.addWidget(QLabel("Maximum Value", self), 1, 0)
        l.addWidget(self.vmax, 1, 1)
        l.addWidget(QLabel("Scale Background", self), 2, 0)
        l.addWidget(self.scaleBg, 2, 1)
        l.addWidget(QLabel("Hue", self), 3, 0)
        l.addWidget(self.hue, 3, 1)
        l.addWidget(QLabel("Exponent", self), 4, 0)
        l.addWidget(self.exp, 4, 1)
        l.addWidget(QLabel("Scale Bar", self), 5, 0)
        l.addWidget(self.scaleBar, 5, 1)
        l.addWidget(self.refreshButton, 6, 0)
        layout = QHBoxLayout()
        layout.addLayout(l)
        layout.addWidget(self.plotWidg)
        self.setLayout(layout)

        self.paint()

    def paint(self):
        """Refresh the recommended regions. If stale is false then just repaint the cached regions without recalculating."""
        if self.parentRoiPlot.data is not self.cachedImage:  # The image has been changed.
            self.cachedImage = self.parentRoiPlot.data
            self.stale = True
        if self.stale:
            try:
                rois = [parm.roi for parm in self.parentRoiPlot.rois]
                data = roiColor(self.parentRoiPlot.data, rois, self.vmin.value(), self.vmax.value(), self.scaleBg.value(), hue=self.hue.value(), exponent=self.exp.value(), numScaleBarPix=self.scaleBar.value())
                self.im.set_data(data)
                self.fig.canvas.draw_idle()
                self.stale = False
            except Exception as e:
                msg = QMessageBox.information(self, "Error", f"Warning: Sin City export failed with error: {str(e)}")
                return


if __name__ == '__main__':
    fPath = r'C:\Users\nicke\Desktop\demo\toast\t\Cell1'
    from pwspy.dataTypes import AcqDir
    from PyQt5.QtWidgets import QApplication
    acq = AcqDir(fPath)
    import sys
    app = QApplication(sys.argv)
    b = RoiPlot(acq, acq.dynamics.getThumbnail())
    b.setWindowTitle("test")
    b.show()
    sys.exit(app.exec())
