import os
import traceback
import re

import matplotlib
import numpy as np
from PyQt5.QtGui import QCursor, QValidator
from PyQt5.QtWidgets import QMenu, QAction, QComboBox, QLabel, QPushButton, QHBoxLayout, QDialog, QWidget, QSlider, QGridLayout, QSpinBox, QDoubleSpinBox, \
    QMessageBox, QVBoxLayout
from PyQt5 import QtCore
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg

from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.bigPlot import BigPlot
from pwspy.dataTypes import Roi, AcqDir
from pwspy.utility.plotting.roiColor import roiColor


class RoiPlot(BigPlot):
    """Adds handling for ROIs to the BigPlot class. It might be smarter to encapsulate Bigplot rather than inherit"""
    def __init__(self, acqDir: AcqDir, data: np.ndarray, title: str, parent=None):
        super().__init__(data, title, parent)
        self.rois = []  # Contains tuples in the form (roi, overlay, poly)

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

        self.setRoiPlotMetadata(acqDir)

        self.annot = self.ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
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
                text += f"\n{self.metadata.pws.pixelSizeUm ** 2 * np.sum(roi.mask):.2f} $μm^2$"
            self.annot.set_text(text)
            self.annot.get_bbox_patch().set_alpha(0.4)

        vis = self.annot.get_visible()
        if event.inaxes == self.ax:
            for roi, overlay, poly in self.rois:
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
            popMenu.popup(cursor.pos())

    def deleteRoiFromPolygon(self, artist):
        for roi, overlay, poly in self.rois:
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
        for roi, overlay, poly in self.rois:
            if overlay is not None:
                overlay.remove()
            poly.remove()
        self.rois = []

    def addRoi(self, roi: Roi):
        if roi.verts is not None:
            poly = roi.getBoundingPolygon()
            poly.set_picker(0)  # allow the polygon to trigger a pickevent
            self.ax.add_patch(poly)
            self.rois.append((roi, None, poly))
        else:  # In the case of old ROI files where the vertices of the outline are not available we have to back-calculate the polygon which does not look good. We make this polygon invisible so it is only used for click detection. we then display an image of the binary mask array.
            overlay = roi.getImage(self.ax) # an image showing the exact shape of the ROI
            poly = roi.getBoundingPolygon() # A polygon used for mouse event handling
            poly.set_visible(False)#poly.set_facecolor((0,0,0,0)) # Make polygon invisible
            poly.set_picker(0) # allow the polygon to trigger a pickevent
            self.ax.add_patch(poly)
            self.rois.append((roi, overlay, poly))

    def _exportAction(self):
        def showSinCityDlg():
            dlg = SinCityDlg(self, self)
            dlg.show()
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
                rois = [roi for roi, overlay, polygon in self.parentRoiPlot.rois]
                data = roiColor(self.parentRoiPlot.data, rois, self.vmin.value(), self.vmax.value(), self.scaleBg.value(), hue=self.hue.value(), exponent=self.exp.value(), numScaleBarPix=self.scaleBar.value())
                self.im.set_data(data)
                self.fig.canvas.draw_idle()
                self.stale = False
            except Exception as e:
                msg = QMessageBox.information(self, "Error", f"Warning: Sin City export failed with error: {str(e)}")
                return


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
