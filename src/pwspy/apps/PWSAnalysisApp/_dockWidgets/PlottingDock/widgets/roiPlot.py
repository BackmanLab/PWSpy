import os
import traceback
import re
import numpy as np
from PyQt5.QtGui import QCursor, QValidator
from PyQt5.QtWidgets import QMenu, QAction, QComboBox, QLabel, QPushButton, QHBoxLayout, QDialog, QWidget, QSlider
from PyQt5 import QtCore

from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.bigPlot import BigPlot
from pwspy.dataTypes import Roi, AcqDir


class RoiPlot(BigPlot):
    """Adds handling for ROIs to the BigPlot class. It might be smarter to encapsulate Bigplot rather than inherit"""
    def __init__(self, acqDir: AcqDir, data: np.ndarray, title: str, parent=None):
        super().__init__(data, title, parent)
        self._rois = []

        self.roiFilter = QComboBox(self)
        self.roiFilter.setEditable(True)
        self.roiFilter.setValidator(WhiteSpaceValidator())

        self.exportButton = QPushButton("Export")
        self.exportButton.released.connect(self._exportAction)

        layout = QHBoxLayout()
        layout.addWidget(QLabel("Roi"), alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.roiFilter)
        layout.addWidget(self.exportButton)
        self.layout().insertLayout(0, layout)

        self.setMetadata(acqDir)

        self.annot = self.ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))

        self._toggleCids = None
        self.enableHoverAnnotation(True)


    def setMetadata(self, metadata: AcqDir):
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
                text += f"\n{self.metadata.pws.pixelSizeUm ** 2 * np.sum(roi.mask):.2f} $μm^2$"
            self.annot.set_text(text)
            self.annot.get_bbox_patch().set_alpha(0.4)

        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            for roi, overlay, poly in self._rois:
                contained, _ = poly.contains(event)
                if contained:
                    if not vis:
                        update_annot(roi, poly)
                        self.annot.set_visible(True)
                        self.fig.canvas.draw_idle()
                    return
            if vis:  # If we got here then no hover actions were found.
                self.annot.set_visible(False)
                self.fig.canvas.draw_idle()

    def _roiPickCallback(self, event):
        if event.mouseevent.button == 3:  # "3" is the right button
            delAction = QAction("Delete ROI", self, triggered=lambda checked, art=event.artist: self.deleteRoiFromPolygon(art))
            popMenu = QMenu(self)
            popMenu.addAction(delAction)

            cursor = QCursor()
            # self.connect(self.figure_canvas, SIGNAL("clicked()"), self.context_menu)
            # self.popMenu.exec_(self.mapToGlobal(event.globalPos()))
            popMenu.popup(cursor.pos())

    def deleteRoiFromPolygon(self, artist):
        for roi, overlay, poly in self._rois:
            if artist is poly:
                roi.deleteRoi(os.path.split(roi.filePath)[0], roi.name, roi.number)
        self.showRois()

    def enableHoverAnnotation(self, enable: bool):
        if enable:
            self._toggleCids = [self.canvas.mpl_connect('motion_notify_event', self._hoverCallback), self.canvas.mpl_connect('pick_event', self._roiPickCallback)]
        else:
            if self._toggleCids:
                [self.canvas.mpl_disconnect(cid) for cid in self._toggleCids]

    def showRois(self):
        pattern = self.roiFilter.currentText()
        self.clearRois()
        for name, num, fformat in self.metadata.getRois():
            if re.fullmatch(pattern, name):
                try:
                    self.addRoi(self.metadata.loadRoi(name, num, fformat))
                except Exception as e:
                    print(f"Failed to load Roi with name: {name}, number: {num}, format: {fformat.name}")
                    traceback.print_exc()
        self.canvas.draw_idle()

    def clearRois(self):
        for roi, overlay, poly in self._rois:
            if overlay is not None:
                overlay.remove()
            poly.remove()
        self._rois = []

    def addRoi(self, roi: Roi):
        if roi.verts is not None:
            poly = roi.getBoundingPolygon()
            poly.set_picker(0)  # allow the polygon to trigger a pickevent
            self.ax.add_patch(poly)
            self._rois.append((roi, None, poly))
        else:  # In the case of old ROI files where the vertices of the outline are not available we have to back-calculate the polygon which does not look good. We make this polygon invisible so it is only used for click detection. we then display an image of the binary mask array.
            overlay = roi.getImage(self.ax) # an image showing the exact shape of the ROI
            poly = roi.getBoundingPolygon() # A polygon used for mouse event handling
            poly.set_visible(False)#poly.set_facecolor((0,0,0,0)) # Make polygon invisible
            poly.set_picker(0) # allow the polygon to trigger a pickevent
            self.ax.add_patch(poly)
            self._rois.append((roi, overlay, poly))

    def _exportAction(self):
        def showSinCityDlg():

        menu = QMenu("Export Menu")
        act = QAction("Sin City Style")
        act.triggered.connect(showSinCityDlg)
        menu.addAction(act)
        menu.exec(self.mapToGlobal(self.exportButton.pos()))

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
    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint)  # Get rid of the close button. this is handled by the selector widget active status
        self.setWindowTitle("Sin City Image Export")

        self.cachedImage = None

        self._paintDebounce = QtCore.QTimer()  # This timer prevents the selectionChanged signal from firing too rapidly.
        self._paintDebounce.setInterval(200)
        self._paintDebounce.setSingleShot(True)
        self._paintDebounce.timeout.connect(self.paint)

        self.adptRangeSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.adptRangeSlider.setToolTip("The image is adaptively thresholded by comparing each pixel value to the average pixel value of gaussian window around the pixel. This value determines how large the area that is averaged will be. Lower values cause the threshold to adapt more quickly.")
        maxImSize = max(parentSelector.image.get_array().shape)
        self.adptRangeSlider.setMaximum(
            maxImSize // 2 * 2 + 1)  # This must be an odd value or else its possible to set the slider to an even value. Opencv doesn't like that.
        self.adptRangeSlider.setMinimum(3)
        self.adptRangeSlider.setSingleStep(2)
        self.adptRangeSlider.setValue(551)
        self.adpRangeDisp = QLabel(str(self.adptRangeSlider.value()), self)

        def adptRangeChanged(val):
            self.stale = True
            self.adpRangeDisp.setText(str(val))
            if self.adptRangeSlider.value() % 2 == 0:
                self.adptRangeSlider.setValue(
                    self.adptRangeSlider.value() // 2 * 2 + 1)  # This shouldn't ever happen. but it sometimes does anyway. make sure that adptRangeSlider is an odd number
            self._paintDebounce.start()

        self.adptRangeSlider.valueChanged.connect(adptRangeChanged)

        self.subSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.subSlider.setMinimum(-50)
        self.subSlider.setMaximum(50)
        self.subSlider.setValue(-10)
        self.subDisp = QLabel(str(self.subSlider.value()), self)

        def subRangeChanged(val):
            self.stale = True
            self.subDisp.setText(str(val))
            self._paintDebounce.start()

        self.subSlider.valueChanged.connect(subRangeChanged)

        self.erodeSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.erodeSlider.setMinimum(0)
        self.erodeSlider.setMaximum(50)
        self.erodeSlider.setValue(10)
        self.erodeDisp = QLabel(str(self.erodeSlider.value()), self)

        def erodeChanged(val):
            self.stale = True
            self.erodeDisp.setText(str(val))
            self.dilateSlider.setMaximum(val)
            self._paintDebounce.start()

        self.erodeSlider.valueChanged.connect(erodeChanged)

        self.dilateSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.dilateSlider.setMinimum(0)
        self.dilateSlider.setMaximum(self.erodeSlider.value())
        self.dilateSlider.setValue(10)
        self.dilateDisp = QLabel(str(self.dilateSlider.value()), self)

        def dilateChanged(val):
            self.stale = True
            self.dilateDisp.setText(str(val))
            self._paintDebounce.start()

        self.dilateSlider.valueChanged.connect(dilateChanged)

        self.simplificationSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.simplificationSlider.setMinimum(0)
        self.simplificationSlider.setMaximum(20)
        self.simplificationSlider.setValue(5)
        self.simDisp = QLabel(str(self.simplificationSlider.value()), self)

        def simpChanged(val):
            self.stale = True
            self.simDisp.setText(str(val))
            self._paintDebounce.start()

        self.simplificationSlider.valueChanged.connect(simpChanged)

        self.minAreaSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.minAreaSlider.setMinimum(5)
        self.minAreaSlider.setMaximum(300)
        self.minAreaSlider.setValue(100)
        self.minAreaDisp = QLabel(str(self.minAreaSlider.value()), self)

        def minAreaChanged(val):
            self.stale = True
            self.minAreaDisp.setText(str(val))
            self._paintDebounce.start()

        self.minAreaSlider.valueChanged.connect(minAreaChanged)

        self.refreshButton = QPushButton("Refresh", self)

        def refreshAction():
            self.stale = True  # Force a full refresh
            self.paint()

        self.refreshButton.released.connect(refreshAction)

        l = QGridLayout()
        l.addWidget(QLabel("Adaptive Range (px)", self), 0, 0)
        l.addWidget(self.adptRangeSlider, 0, 1)
        l.addWidget(self.adpRangeDisp, 0, 2)
        l.addWidget(QLabel("Threshold Offset", self), 1, 0)
        l.addWidget(self.subSlider, 1, 1)
        l.addWidget(self.subDisp, 1, 2)
        l.addWidget(QLabel("Erode (px)", self), 2, 0)
        l.addWidget(self.erodeSlider, 2, 1)
        l.addWidget(self.erodeDisp, 2, 2)
        l.addWidget(QLabel("Dilate (px)", self), 3, 0)
        l.addWidget(self.dilateSlider, 3, 1)
        l.addWidget(self.dilateDisp, 3, 2)
        l.addWidget(QLabel("Simplification", self), 4, 0)
        l.addWidget(self.simplificationSlider, 4, 1)
        l.addWidget(self.simDisp, 4, 2)
        l.addWidget(QLabel("Minimum Area (px)", self), 5, 0)
        l.addWidget(self.minAreaSlider, 5, 1)
        l.addWidget(self.minAreaDisp, 5, 2)
        l.addWidget(self.refreshButton, 6, 0)
        self.setLayout(l)

    def show(self):
        super().show()

    def paint(self):
        """Refresh the recommended regions. If stale is false then just repaint the cached regions without recalculating."""
        if self.parentSelector.image.get_array() is not self.cachedImage:  # The image has been changed.
            self.cachedImage = self.parentSelector.image.get_array()
            self.stale = True
        if self.stale:
            try:
                polys = segmentAdaptive(self.parentSelector.image.get_array(), minArea=self.minAreaSlider.value(), adaptiveRange=self.adptRangeSlider.value(),
                                        thresholdOffset=self.subSlider.value(), polySimplification=self.simplificationSlider.value(),
                                        erode=self.erodeSlider.value(), dilate=self.dilateSlider.value())
                self.cachedRegions = polys
                self.stale = False
            except Exception as e:
                print("Warning: adaptive segmentation failed with error: ", e)
                return
        else:
            polys = self.cachedRegions
        self.parentSelector.reset()
        self.parentSelector.drawRois(polys)



if __name__ == '__main__':
    fPath = r'G:\Aya_NAstudy\matchedNAi_largeNAc\cells\Cell2'
    from pwspy.dataTypes import AcqDir
    from PyQt5.QtWidgets import QApplication
    acq = AcqDir(fPath)
    import sys
    app = QApplication(sys.argv)
    b = RoiPlot(acq, acq.pws.getThumbnail(), "Test")
    b.show()
    sys.exit(app.exec())
