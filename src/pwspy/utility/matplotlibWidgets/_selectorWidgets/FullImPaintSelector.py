from typing import List

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QDialog, QWidget, QSlider, QLabel, QPushButton, QGridLayout
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
        image: A reference to a matplotlib `AxesImage`. The data from this object is used to detect bright regions.
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
        self._checkImageChangeTimer.timeout.connect(self.paint)


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
            # rect.moveTo(self.ax.figure.canvas.mapToGlobal(QPoint(parentRect.x() + parentRect.width() - rect.width(), parentRect.y())))
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
                    print("Error: FullImPaintSelecte.drawROis tried to draw a polygon of a shapely.MultiPolygon object.")
                    continue
                p = Polygon(poly.exterior.coords, color=color['color'], animated=True)
                self.addArtist(p)
                self.axMan.update()

    def _press(self, event):
        """If a displayed polygon is clicked on then execute the `onselect` callback."""
        if event.button == 1:  # Left Click
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

    def paint(self):
        """Refresh the detected regions. If stale is false then just repaint the cached regions without recalculating."""
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
            polys = self._cachedRegions
        self.reset()
        self._drawRois(polys)
        self._stale = False


def valChanged(self):
    """A decorator for callbacks associated with a change in the adaptivePainDialog settings."""
    def decorator(func):
        def newFunc(val):
            self._stale = True
            func(val)
            self._paintDebounce.start()
        return newFunc
    return decorator

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

        self.adptRangeSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.adptRangeSlider.setToolTip("The image is adaptively thresholded by comparing each pixel value to the average pixel value of gaussian window around the pixel. This value determines how large the area that is averaged will be. Lower values cause the threshold to adapt more quickly.")
        maxImSize = max(parentSelector.image.get_array().shape)
        self.adptRangeSlider.setMaximum(maxImSize//2*2+1) #This must be an odd value or else its possible to set the slider to an even value. Opencv doesn't like that.
        self.adptRangeSlider.setMinimum(3)
        self.adptRangeSlider.setSingleStep(2)
        #TODO recommend value based on expected pixel size of a nucleus. need to access metadata.
        #TODO add tooltips explaining each step.
        self.adptRangeSlider.setValue(551)
        self.adpRangeDisp = QLabel(str(self.adptRangeSlider.value()), self)

        @valChanged(self)
        def adptRangeChanged(val):
            self.adpRangeDisp.setText(str(val))
            if self.adptRangeSlider.value() % 2 == 0:
                self.adptRangeSlider.setValue(self.adptRangeSlider.value()//2*2+1)#This shouldn't ever happen. but it sometimes does anyway. make sure that adptRangeSlider is an odd number

        self.adptRangeSlider.valueChanged.connect(adptRangeChanged)

        self.subSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.subSlider.setMinimum(-50)
        self.subSlider.setMaximum(50)
        self.subSlider.setValue(-10)
        self.subDisp = QLabel(str(self.subSlider.value()), self)

        @valChanged(self)
        def subRangeChanged(val):
            self.subDisp.setText(str(val))

        self.subSlider.valueChanged.connect(subRangeChanged)

        self.erodeSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.erodeSlider.setMinimum(0)
        self.erodeSlider.setMaximum(50)
        self.erodeSlider.setValue(10)
        self.erodeDisp = QLabel(str(self.erodeSlider.value()), self)

        @valChanged(self)
        def erodeChanged(val):
            self.erodeDisp.setText(str(val))
            self.dilateSlider.setMaximum(val)

        self.erodeSlider.valueChanged.connect(erodeChanged)

        self.dilateSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.dilateSlider.setMinimum(0)
        self.dilateSlider.setMaximum(self.erodeSlider.value())
        self.dilateSlider.setValue(10)
        self.dilateDisp = QLabel(str(self.dilateSlider.value()), self)

        @valChanged(self)
        def dilateChanged(val):
            self.dilateDisp.setText(str(val))

        self.dilateSlider.valueChanged.connect(dilateChanged)

        self.simplificationSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.simplificationSlider.setMinimum(0)
        self.simplificationSlider.setMaximum(20)
        self.simplificationSlider.setValue(5)
        self.simDisp = QLabel(str(self.simplificationSlider.value()), self)

        @valChanged(self)
        def simpChanged(val):
            self.simDisp.setText(str(val))

        self.simplificationSlider.valueChanged.connect(simpChanged)

        self.minAreaSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.minAreaSlider.setMinimum(5)
        self.minAreaSlider.setMaximum(300)
        self.minAreaSlider.setValue(100)
        self.minAreaDisp = QLabel(str(self.minAreaSlider.value()), self)

        @valChanged(self)
        def minAreaChanged(val):
            self.minAreaDisp.setText(str(val))

        self.minAreaSlider.valueChanged.connect(minAreaChanged)

        self.refreshButton = QPushButton("Refresh", self)
        def refreshAction():
            self._stale = True  # Force a full refresh
            self.parentSelector.paint()
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

