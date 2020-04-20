from typing import List

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QDialog, QWidget, QSlider, QLabel, QPushButton, QGridLayout, QHBoxLayout, QFormLayout
from cycler import cycler
from matplotlib.image import AxesImage
from shapely.geometry import Polygon as shapelyPolygon, LinearRing, MultiPolygon
from matplotlib.patches import Polygon

from pwspy.utility.fluorescence import segmentAdaptive
from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._selectorWidgets import SelectorWidgetBase


class FullImPaintSelector(SelectorWidgetBase):
    """Uses adaptive thresholding in an attempt to highlight all bright selectable regions in a fluorescence image.

    Args:
        axMan: The manager for a matplotlib `Axes` that you want to interact with.
        im: A reference to a matplotlib `AxesImage`. The data from this object is used to detect bright regions.
        onselect: A callback that will be called when the user hits 'enter'. Should have signature (polygonCoords, sparseHandleCoords).
    """
    def __init__(self, axMan: AxManager, im: AxesImage, onselect=None):
        super().__init__(axMan, im, onselect=onselect)
        self.dlg = AdaptivePaintDialog(self, self.ax.figure.canvas)

        self._stale = True #This tells us whether we can load regions from the cache or need to recalculate
        self._cachedRegions = None # We cache the detected polygons. No need to redetect if nothing has changed between selections.
        self._cachedImage = None # We cache a reference to the image data as a way of detecting when the image data has changed.

        self._checkImageChangeTimer = QtCore.QTimer()  # This timer checks if the image data has been changed. If it has then redetect regions.
        self._checkImageChangeTimer.setInterval(1000)
        self._checkImageChangeTimer.setSingleShot(False)
        self._checkImageChangeTimer.timeout.connect(lambda: self.paint(forceRedraw=False))
        self._checkImageChangeTimer.start()

    def __del__(self):
        self._checkImageChangeTimer.stop()

    @staticmethod
    def getHelpText():
        return "Segment a full image using opencv thresholding techniques."

    def reset(self):
        """Reset the state of the selector so it's ready for a new selection."""
        self.removeArtists()

    def set_active(self, active: bool):
        super().set_active(active)
        if active:
            self.dlg.show()
            # Move dialog to the side
            rect = self.dlg.geometry()
            parentRect = self.ax.figure.canvas.geometry()
            rect.moveTo(self.ax.figure.canvas.mapToGlobal(QPoint(parentRect.x() - rect.width(), parentRect.y())))
            self.dlg.setGeometry(rect)
            self.paint()
        else:
            self.dlg.close()

    def _drawRois(self, polys: List[shapelyPolygon]):
        """Convert a list of shapely `Polygon` objects into matplotlib `Polygon`s and display them."""
        self._cachedRegions = polys
        if len(polys) > 0:
            alpha = 0.3
            colorCycler = cycler(color=[(1, 0, 0, alpha), (0, 1, 0, alpha), (0, 0, 1, alpha), (1, 1, 0, alpha), (1, 0, 1, alpha)])
            for poly, color in zip(polys, colorCycler()):
                if isinstance(poly, MultiPolygon):
                    print("Error: FullImPaintSelector.drawRois tried to draw a polygon of a shapely.MultiPolygon object.")
                    continue
                p = Polygon(poly.exterior.coords, color=color['color'], animated=True)
                self.addArtist(p)
                self.axMan.update()

    def _press(self, event):
        """If a displayed polygon is clicked on then execute the `onselect` callback."""
        if event.button == 1 and self.onselect is not None:  # Left Click
            coord = (event.xdata, event.ydata)
            for artist in self.artists:
                assert isinstance(artist, Polygon)
                if artist.get_path().contains_point(coord):
                    l = shapelyPolygon(LinearRing(artist.xy))
                    l = l.simplify(l.length / 2e2, preserve_topology=False)
                    if isinstance(l, MultiPolygon):  # There is a chance for this to convert a Polygon to a Multipolygon.
                        l = max(l, key=lambda a: a.area)  # To fix this we extract the largest polygon from the multipolygon
                    handles = l.exterior.coords
                    self.onselect(artist.xy, handles)
                    break

    def paint(self, forceRedraw: bool = True):
        """Refresh the detected regions.

        Args:
            forceRedraw: If `True` then polygons will be cleared and redrawn even if we don't detect that our status is `stale`
        """
        if self.image.get_array() is not self._cachedImage:  # The image has been changed.
            self._cachedImage = self.image.get_array()
            self._stale = True
        if self.dlg.isStale():
            self._stale = True
        if self._stale:
            try:
                polys = segmentAdaptive(self.image.get_array(), **self.dlg.getSettings())
            except Exception as e:
                print("Warning: adaptive segmentation failed with error: ", e)
                return
        else:
            if forceRedraw:
                polys = self._cachedRegions
            else:
                return
        self.reset()
        self._drawRois(polys)
        self._stale = False


class LabeledSlider(QWidget):
    """A slider with a label that indicates the current value."""
    def __init__(self, Min, Max, Step, Value, parent=None):
        super().__init__(parent)
        self.display = QLabel(self)
        self.slider = QSlider(QtCore.Qt.Horizontal, self)

        self.slider.valueChanged.connect(lambda val: self.display.setText(str(val)))

        self.setMaximum = lambda val: self.slider.setMaximum(val)
        self.setMinimum = lambda val: self.slider.setMinimum(val)
        self.setSingleStep = lambda val: self.slider.setSingleStep(val)
        self.setValue = lambda val: self.slider.setValue(val)
        self.value = lambda: self.slider.value()
        self.valueChanged = self.slider.valueChanged

        l = QHBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(self.slider)
        l.addWidget(self.display)
        l.setStretch(0, 0)
        l.setStretch(1, 1)
        self.setLayout(l)

        self.setMinimum(Min)
        self.setMaximum(Max)
        self.setSingleStep(Step)
        self.setValue(Value)


class AdaptivePaintDialog(QDialog):
    """The dialog used by the FullImPaintSelector. Can adjust detection parameters.

    Args:
        parentSelector: A reference the the `FullImPaintSelector` that is being used with this dialog.
        parent: A QWidget to serve as the Qt parent for this QWidget.
    """
    def __init__(self, parentSelector: FullImPaintSelector, parent: QWidget):
        super().__init__(parent=parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.WindowTitleHint | QtCore.Qt.CustomizeWindowHint) #Get rid of the close button. this is handled by the selector widget active status
        self.parentSelector = parentSelector
        self.setWindowTitle("Adaptive Painter")

        self._stale = True  # Keeps track of if the settings have changed.

        self._paintDebounce = QtCore.QTimer()  # This timer prevents the selectionChanged signal from firing too rapidly.
        self._paintDebounce.setInterval(200)
        self._paintDebounce.setSingleShot(True)
        self._paintDebounce.timeout.connect(self.parentSelector.paint)

        def _valChanged():
            """When a setting is changed it should call this to schedule a repaint."""
            self._stale = True
            self._paintDebounce.start()

        maxImSize = max(parentSelector.image.get_array().shape)
        self.adptRangeSlider = LabeledSlider(3, maxImSize//2*2+1, 2, 551) # This must always have an odd value or opencv will have an error.
        #TODO recommend value based on expected pixel size of a nucleus. need to access metadata.

        def adptRangeChanged(val):
            _valChanged()
            if self.adptRangeSlider.value() % 2 == 0:
                self.adptRangeSlider.setValue(self.adptRangeSlider.value()//2*2+1)#This shouldn't ever happen. but it sometimes does anyway. make sure that adptRangeSlider is an odd number

        self.adptRangeSlider.valueChanged.connect(adptRangeChanged)

        self.subSlider = LabeledSlider(-50, 50, 1, -10, self)
        self.subSlider.valueChanged.connect(_valChanged)

        self.erodeSlider = LabeledSlider(0, 50, 1, 10, self)
        def erodeChanged(val):
            _valChanged()
            self.dilateSlider.setMaximum(val)
        self.erodeSlider.valueChanged.connect(erodeChanged)

        self.dilateSlider = LabeledSlider(0, self.erodeSlider.value(), 1, 10, self)
        self.dilateSlider.valueChanged.connect(_valChanged)

        self.simplificationSlider = LabeledSlider(0, 20, 1, 5, self)
        self.simplificationSlider.valueChanged.connect(_valChanged)

        self.minAreaSlider = LabeledSlider(5, 300, 1, 100, self)
        self.minAreaSlider.valueChanged.connect(_valChanged)

        self.refreshButton = QPushButton("Refresh", self)
        def refreshAction():
            self._stale = True  # Force a full refresh
            self.parentSelector.paint()
        self.refreshButton.released.connect(refreshAction)

        self.adptRangeSlider.setToolTip("The image is adaptively thresholded by comparing each pixel value to the average pixel value of gaussian window around the pixel. This value determines how large the area that is averaged will be. Lower values cause the threshold to adapt more quickly.")
        self.subSlider.setToolTip("This offset is passed to `cv2.adaptiveThreshold` and sets the threshold the segmentation process")
        self.erodeSlider.setToolTip("The number of pixels that the polygons should be eroded by. Combining this with dilation can help to close gaps.")
        self.dilateSlider.setToolTip("The number of pixels that the polygons should be dilated by.")
        self.simplificationSlider.setToolTip("This parameter will simplify the edges of the detected polygons to remove overly complicated geometry.")
        self.minAreaSlider.setToolTip("Detected regions with a pixel area lower than this value will be discarded.")

        l = QFormLayout()
        l.addRow("Adaptive Range (px):", self.adptRangeSlider)
        l.addRow("Threshold Offset:", self.subSlider)
        l.addRow("Erode (px):", self.erodeSlider)
        l.addRow("Dilate (px):", self.dilateSlider)
        l.addRow("Simplification:", self.simplificationSlider)
        l.addRow("Minimum Area (px):", self.minAreaSlider)
        l.addRow(self.refreshButton)
        self.setLayout(l)

    def isStale(self):
        """Returns if True if the settings have changed since the last time `getSettings` was called."""
        return self._stale

    def getSettings(self) -> dict:
        self._stale = False
        return dict(
            minArea=self.minAreaSlider.value(), adaptiveRange=self.adptRangeSlider.value(),
            thresholdOffset=self.subSlider.value(), polySimplification=self.simplificationSlider.value(),
            erode=self.erodeSlider.value(), dilate=self.dilateSlider.value()
        )

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import numpy as np

    fig, ax = plt.subplots()
    im = ax.imshow(np.random.random((100, 100)))
    sel = FullImPaintSelector(AxManager(ax), im)
    fig.show()
    plt.pause(.1)
    sel.set_active(True)
    plt.show()
