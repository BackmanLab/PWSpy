import numpy as np
from cycler import cycler
from matplotlib.image import AxesImage
from matplotlib.patches import Rectangle, Polygon
from shapely.geometry import Polygon as shapelyPolygon, LinearRing, MultiPolygon

from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets.selectorWidgets import SelectorWidgetBase


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
        import cv2
        x, y = rect.xy
        x = int(x)
        y = int(y)
        x2 = int(x + rect.get_width())
        y2 = int(y + rect.get_height())
        xslice = slice(x, x2+1) if x2 > x else slice(x2, x+1)
        yslice = slice(y, y2+1) if y2 > y else slice(y2, y+1)
        image = self.image.get_array()[(yslice, xslice)]
        image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8)
        threshold, binary = cv2.threshold(image, 0, 1, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
        contImage, contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        alpha = 0.3
        colorCycler = cycler(color=[(1, 0, 0, alpha), (0, 1, 0, alpha), (0, 0, 1, alpha), (1, 1, 0, alpha), (1, 0, 1, alpha)])
        polys = []
        for contour in contours:
            contour = contour.squeeze()  # We want a Nx2 array. We get Nx1x2 though.
            if len(contour.shape) != 2:  # Sometimes contour is 1x1x2 which squezes down to just 2
                continue
            if contour.shape[0] < 3:  # We need a polygon, not a line
                continue
            contour += np.array([xslice.start, yslice.start])  # Apply offset so that coordinates are globally correct.
            p = shapelyPolygon(contour)
            if p.area < 100:  # Reject small regions
                continue
            polys.append(p)
        if len(polys) > 0:
            areas, polys = zip(*sorted(zip([p.area for p in polys], polys)))  # Sort by size
            for poly, color in zip(polys, colorCycler()):
                p = Polygon(poly.exterior.coords, color=color['color'], animated=True)
                self.addArtist(p)
                self.contours.append(p)
                self.axMan.update()

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
                self.findContours(Rectangle((0, 0), self.image.get_array().shape[0], self.image.get_array().shape[1]))
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