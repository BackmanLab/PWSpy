from __future__ import annotations
import re

import numpy as np
from PyQt5 import QtCore
from PyQt5.QtGui import QCursor, QValidator
from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QDoubleSpinBox, QPushButton, QLabel, QGridLayout, QComboBox, \
    QAction, QMenu
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pwspy.apps.PWSAnalysisApp._sharedWidgets.rangeSlider import QRangeSlider
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ICMetaData
from pwspy.dataTypes import Roi
import os


class BigPlot(QWidget):
    def __init__(self, metadata: ICMetaData, data: np.ndarray, title: str, parent=None):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        self.setWindowTitle(title)
        layout = QGridLayout()
        self._rois = []
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.get_yaxis().set_visible(False)
        self.ax.get_xaxis().set_visible(False)
        self.im = self.ax.imshow(data, cmap='gray')
        self.fig.colorbar(self.im, ax=self.ax)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        self.slider = QRangeSlider(self)
        self.slider.endValueChanged.connect(self.climImage)
        self.slider.startValueChanged.connect(self.climImage)
        self.autoDlg = SaturationDialog(self)
        self.autoDlg.accepted.connect(self.setSaturation)
        self.rangeDlg = RangeDialog(self)
        self.rangeDlg.accepted.connect(self.setRange)
        self.saturationButton = QPushButton("Auto")
        self.saturationButton.released.connect(self.autoDlg.show)
        self.manualRangeButton = QPushButton("Range")
        self.manualRangeButton.released.connect(self.rangeDlg.show)
        self.roiFilter = QComboBox(self)
        self.roiFilter.setEditable(True)
        self.roiFilter.setValidator(WhiteSpaceValidator())

        self.cmapCombo = QComboBox(self)
        self.cmapCombo.addItems(['gray', 'jet', 'plasma', 'Reds'])
        self.cmapCombo.currentTextChanged.connect(self.changeCmap)

        layout.addWidget(self.canvas, 0, 0, 8, 8)
        layout.addWidget(QLabel("Color Range"), 9, 0, 1, 1)
        layout.addWidget(self.slider, 9, 1, 1, 4)
        layout.addWidget(self.saturationButton, 9, 6, 1, 1)
        layout.addWidget(self.manualRangeButton, 9, 7, 1, 1)
        layout.addWidget(NavigationToolbar(self.canvas, self), 10, 0, 1, 4)
        layout.addWidget(QLabel("Roi"), 10, 4, 1, 1, alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.roiFilter, 10, 5, 1, 1)
        layout.addWidget(QLabel("Color Map"), 10, 6, 1, 1, alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.cmapCombo, 10, 7, 1, 1)
        layout.setRowStretch(0, 1)  # This causes the plot to take up all the space that isn't needed by the other widgets.
        self.setLayout(layout)

        self.setMetadata(metadata)
        self.setImageData(data)

        self.show()
        self.setSaturation()

        self.annot = self.ax.annotate("", xy=(0, 0), xytext=(20, 20), textcoords="offset points",
                            bbox=dict(boxstyle="round", fc="w"),
                            arrowprops=dict(arrowstyle="->"))

        self._toggleCids = None
        self.enableHoverAnnotation(True)

    def setImageData(self, data: np.ndarray):
        self.data = data
        self.im.set_data(data)
        self.slider.setMax(self.data.max())
        self.slider.setMin(self.data.min())
        self.canvas.draw_idle()

    def setMetadata(self, metadata: ICMetaData):
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


    def _hoverCallback(self, event):
        def update_annot(roi, poly):
            self.annot.xy = poly.xy.mean(axis=0) # Set the location to the center of the polygon.
            text = f"{roi.name}, {roi.number}"
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
            if vis: #If we got here then no hover actions were found.
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
                self.addRoi(self.metadata.loadRoi(name, num, fformat))
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
            poly.set_picker(0) # allow the polygon to trigger a pickevent
            self.ax.add_patch(poly)
            self._rois.append((roi, None, poly))
        else:
            overlay = roi.getImage(self.ax) # an image showing the exact shape of the ROI
            poly = roi.getBoundingPolygon() # A polygon used for mouse event handling
            poly.set_visible(False)#poly.set_facecolor((0,0,0,0)) # Make polygon invisible
            poly.set_picker(0) # allow the polygon to trigger a pickevent
            self.ax.add_patch(poly)
            self._rois.append((roi, overlay, poly))

    def setSaturation(self):
        percentage = self.autoDlg.value
        m = np.percentile(self.data, percentage)
        M = np.percentile(self.data, 100 - percentage)
        self.slider.setStart(m)
        self.slider.setEnd(M)

    def setRange(self):
        self.slider.setStart(self.rangeDlg.minimum)
        self.slider.setEnd(self.rangeDlg.maximum)

    def climImage(self):
        self.im.set_clim((self.slider.start(), self.slider.end()))
        self.canvas.draw_idle()

    def changeCmap(self, cMap: str):
        self.im.set_cmap(cMap)
        self.canvas.draw_idle()


class SaturationDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent, flags=QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        l = QVBoxLayout()
        self.numBox = QDoubleSpinBox()
        self.numBox.setValue(0.1)
        self.numBox.setMinimum(0)
        self.numBox.setSingleStep(0.1)
        self.okButton = QPushButton("Ok")
        self.okButton.released.connect(self.accept)
        l.addWidget(QLabel("Saturation %"))
        l.addWidget(self.numBox)
        l.addWidget(self.okButton)
        self.setLayout(l)

    @property
    def value(self):
        return self.numBox.value()


class RangeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent, flags=QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        l = QGridLayout()
        self.minBox = QDoubleSpinBox()

        self.maxBox = QDoubleSpinBox()
        self.okButton = QPushButton("Ok")
        self.okButton.released.connect(self.accept)
        l.addWidget(QLabel("Min"), 0, 0, 1, 1)
        l.addWidget(QLabel("Max"), 0, 1, 1, 1)
        l.addWidget(self.minBox, 1, 0, 1, 1)
        l.addWidget(self.maxBox, 1, 1, 1, 1)
        l.addWidget(self.okButton, 2, 1, 1, 1)
        self.setLayout(l)

    def show(self):
        for b in [self.minBox, self.maxBox]:
            b.setMaximum(self.parent().slider.max())
            b.setMinimum(self.parent().slider.min())
        self.minBox.setValue(self.parent().slider.start())
        self.maxBox.setValue(self.parent().slider.end())
        super().show()

    @property
    def minimum(self): return self.minBox.value()

    @property
    def maximum(self): return self.maxBox.value()


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
