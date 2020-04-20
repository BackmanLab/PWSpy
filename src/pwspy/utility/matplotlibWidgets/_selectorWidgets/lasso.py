from matplotlib.image import AxesImage
from matplotlib.patches import Polygon
from shapely.geometry import Polygon as shapelyPolygon, LinearRing

from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._selectorWidgets import SelectorWidgetBase


class LassoSelector(SelectorWidgetBase):
    def __init__(self, axMan: AxManager, image: AxesImage, onselect=None):
        super().__init__(axMan, image)
        self.onselect = onselect
        self.verts = None
        self.polygon = Polygon([[0,0]], facecolor=(0, 0, 1, .1), animated=True, edgecolor=(0, 0, 1, .8))
        self.polygon.set_visible(False)
        self.addArtist(self.polygon)
#        self.set_active(True) #needed for blitting to work

    @staticmethod
    def getHelpText():
        return "Click and drag to draw a freehand shape."

    def reset(self):
        self.verts = None
        self.polygon.set_visible(False)

    def _press(self, event):
        self.verts = [(event.xdata, event.ydata)]
        self.set_visible(True)

    def _release(self, event):
        if event.button == 1: #Left click
            if (self.verts is not None) and (self.onselect is not None):
                l = shapelyPolygon(LinearRing(self.verts))
                l = l.buffer(0)
                l = l.simplify(l.length / 2e2, preserve_topology=False)
                handles = l.exterior.coords
                self.onselect(self.verts, handles)

    def _ondrag(self, event):
        if self.verts is None:
            return
        self.verts.append((event.xdata, event.ydata))
        self.polygon.set_xy(self.verts)
        self.axMan.update()