from typing import List

from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QDialog, QWidget, QGridLayout, QSlider, QPushButton, QLabel
from cycler import cycler
from matplotlib.image import AxesImage
from matplotlib.patches import Rectangle, Polygon
from shapely.geometry import Polygon as shapelyPolygon, LinearRing, MultiPolygon
import shapely
from pwspy.utility.fluorescence.segmentation import segmentOtsu, segmentAdaptive
from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._selectorWidgets import SelectorWidgetBase



class PaintSelector(SelectorWidgetBase):
    def __init__(self, axMan: AxManager, im: AxesImage, onselect=None):
        super().__init__(axMan, im)
        self.onselect = onselect
        self.started = False
        self.selectionTime = False
        self.contours = []
        self.box = Rectangle((0, 0), 0, 0, facecolor = (1, 0, 1, 0.01), edgecolor=(0, 0, 1, 0.4), animated=True)
        self.addArtist(self.box)

    @staticmethod
    def getHelpText():
        return "Click and drag to select a rectangular region to search for objects. Then click the object you would like to select. Press `a` to select the whole image."

    def reset(self):
        self.started = False
        [self.removeArtist(i) for i in self.contours]
        self.contours = []
        self.selectionTime = False

    def findContours(self, rect: Rectangle):
        x, y = rect.xy
        x = int(x)
        y = int(y)
        x2 = int(x + rect.get_width())
        y2 = int(y + rect.get_height())
        xslice = slice(x, x2+1) if x2 > x else slice(x2, x+1)
        yslice = slice(y, y2+1) if y2 > y else slice(y2, y+1)
        image = self.image.get_array()[(yslice, xslice)]
        polys = segmentOtsu(image)
        for i in range(len(polys)):  # Apply offset so that coordinates are globally correct.
            polys[i] = shapely.affinity.translate(polys[i], xslice.start, yslice.start)
        self.drawRois(polys)

    def drawRois(self, polys: List[shapelyPolygon]):
        if len(polys) > 0:
            alpha = 0.3
            colorCycler = cycler(color=[(1, 0, 0, alpha), (0, 1, 0, alpha), (0, 0, 1, alpha), (1, 1, 0, alpha), (1, 0, 1, alpha)])
            for poly, color in zip(polys, colorCycler()):
                p = Polygon(poly.exterior.coords, color=color['color'], animated=True)
                self.addArtist(p)
                self.contours.append(p)
                self.axMan.update()

    def findAdaptiveContours(self):
        dlg = AdaptivePaintDialog(self, self.ax.figure.canvas)
        #Move dialog to the side
        dlg.show()
        rect = dlg.geometry()
        parentRect = self.ax.figure.canvas.geometry()
        # rect.moveTo(self.ax.figure.canvas.mapToGlobal(QPoint(parentRect.x() + parentRect.width() - rect.width(), parentRect.y())))
        rect.moveTo(self.ax.figure.canvas.mapToGlobal(QPoint(parentRect.x() - rect.width(), parentRect.y())))

        dlg.setGeometry(rect)
        dlg.exec()

    def _press(self, event):
        if event.button == 1:  # Left Click
            if not self.started and not self.selectionTime:
                self.started = True
                self.box.set_xy((event.xdata, event.ydata))
            elif self.selectionTime:
                coord = (event.xdata, event.ydata)
                for artist in self.contours:
                    assert isinstance(artist, Polygon)
                    if artist.get_path().contains_point(coord):
                        l = shapelyPolygon(LinearRing(artist.xy))
                        l = l.simplify(l.length / 2e2, preserve_topology=False)
                        if isinstance(l, MultiPolygon):# There is a chance for this to convert a Polygon to a Multipolygon.
                            l = max(l, key=lambda a: a.area) #To fix this we extract the largest polygon from the multipolygon
                        handles = l.exterior.coords
                        self.onselect(artist.xy, handles)
                        break
                self.reset()

    def _on_key_press(self, event):
        if event.key.lower() == 'a':
            if self.selectionTime:
                self.reset()
            if not self.started and not self.selectionTime:
                self.started = True
                # self.findContours(Rectangle((0, 0), self.image.get_array().shape[0], self.image.get_array().shape[1]), func=segmentAdaptive)
                self.findAdaptiveContours()
                self.selectionTime = True
                self.started = False


    def _ondrag(self, event):
        if self.started and event.button == 1:
            x, y = self.box.xy
            dx = event.xdata - x
            dy = event.ydata - y
            self.box.set_width(dx)
            self.box.set_height(dy)
            self.axMan.update()

    def _release(self, event):
        if event.button == 1 and self.started:
            self.findContours(self.box)
            self.selectionTime = True
            self.started = False

class AdaptivePaintDialog(QDialog):
    def __init__(self, parentSelector: PaintSelector, parent: QWidget):
        super().__init__(parent=parent)
        self.parentSelector = parentSelector
        self.setModal(True)
        
        self._paintDebounce = QtCore.QTimer()  # This timer prevents the selectionChanged signal from firing too rapidly.
        self._paintDebounce.setInterval(200)
        self._paintDebounce.setSingleShot(True)
        self._paintDebounce.timeout.connect(self.paint)

        self.adptRangeSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.adptRangeSlider.setMaximum(parentSelector.image.get_array().shape[0])
        self.adptRangeSlider.setMinimum(3)
        self.adptRangeSlider.setSingleStep(2)
        #TODO recommend value based on expected pixel size of a nucleus. need to access metadata.
        self.adptRangeSlider.setValue(101)
        self.adpRangeDisp = QLabel(str(self.adptRangeSlider.value()), self)
        def adptRangeChanged(val):
            self.adpRangeDisp.setText(str(val))
            if self.adptRangeSlider.value() % 2 == 0:
                self.adptRangeSlider.setValue(self.adptRangeSlider.value()//2*2+1)#This shouldn't ever happen. but it sometimes does anyway. make sure that adptRangeSlider is an odd number
            self._paintDebounce.start()
        self.adptRangeSlider.valueChanged.connect(adptRangeChanged)

        self.subSlider = QSlider(QtCore.Qt.Horizontal, self)
        self.subSlider.setMinimum(-50)
        self.subSlider.setMaximum(50)
        self.subSlider.setValue(-10)
        self.subDisp = QLabel(str(self.subSlider.value()), self)
        def subRangeChanged(val):
            self.subDisp.setText(str(val))
            self._paintDebounce.start()
        self.subSlider.valueChanged.connect(subRangeChanged)

        self.okbutton = QPushButton("OK", self)

        self.okbutton.released.connect(self.paint)

        l = QGridLayout()
        l.addWidget(QLabel("Adaptive Range", self), 0, 0)
        l.addWidget(self.adptRangeSlider, 0, 1)
        l.addWidget(self.adpRangeDisp, 0, 2)
        l.addWidget(QLabel("Subb", self), 1, 0)
        l.addWidget(self.subSlider, 1, 1)
        l.addWidget(self.subDisp, 1, 2)
        l.addWidget(self.okbutton)
        self.setLayout(l)

    def paint(self):
        polys = segmentAdaptive(self.parentSelector.image.get_array(), adaptiveRange=self.adptRangeSlider.value(), subtract=self.subSlider.value())
        self.parentSelector.reset()
        self.parentSelector.drawRois(polys)