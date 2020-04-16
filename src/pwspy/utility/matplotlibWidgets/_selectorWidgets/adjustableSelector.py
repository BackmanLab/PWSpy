from typing import Type

from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from scipy import interpolate
import numpy as np

from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._selectorWidgets import SelectorWidgetBase


def pnt2line(pnt, start, end):
    import math
    # Given a line with coordinates 'start' and 'end' and the
    # coordinates of a point 'pnt' the proc returns the shortest
    # distance from pnt to the line and the coordinates of the
    # nearest point on the line.
    #
    # 1  Convert the line segment to a vector ('line_vec').
    # 2  Create a vector connecting start to pnt ('pnt_vec').
    # 3  Find the length of the line vector ('line_len').
    # 4  Convert line_vec to a unit vector ('line_unitvec').
    # 5  Scale pnt_vec by line_len ('pnt_vec_scaled').
    # 6  Get the dot product of line_unitvec and pnt_vec_scaled ('t').
    # 7  Ensure t is in the range 0 to 1.
    # 8  Use t to get the nearest location on the line to the end
    #    of vector pnt_vec_scaled ('nearest').
    # 9  Calculate the distance from nearest to pnt_vec_scaled.
    # 10 Translate nearest back to the start/end line.
    # Malcolm Kesson 16 Dec 2012
    def dot(v, w):
        x, y, z = v
        X, Y, Z = w
        return x * X + y * Y + z * Z

    def length(v):
        x, y, z = v
        return math.sqrt(x * x + y * y + z * z)

    def vector(b, e):
        x, y, z = b
        X, Y, Z = e
        return (X - x, Y - y, Z - z)

    def unit(v):
        x, y, z = v
        mag = length(v)
        return (x / mag, y / mag, z / mag)

    def distance(p0, p1):
        return length(vector(p0, p1))

    def scale(v, sc):
        x, y, z = v
        return (x * sc, y * sc, z * sc)

    def add(v, w):
        x, y, z = v
        X, Y, Z = w
        return (x + X, y + Y, z + Z)

    line_vec = vector(start, end)
    pnt_vec = vector(start, pnt)
    line_len = length(line_vec)
    line_unitvec = unit(line_vec)
    pnt_vec_scaled = scale(pnt_vec, 1.0 / line_len)
    t = dot(line_unitvec, pnt_vec_scaled)
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    nearest = scale(line_vec, t)
    dist = distance(nearest, pnt_vec)
    nearest = add(nearest, start)
    return (dist, nearest)


class PolygonInteractor(SelectorWidgetBase):
    """
    A polygon editor.
    https://matplotlib.org/gallery/event_handling/poly_editor.html
    Key-bindings:
        't' toggle vertex markers on and off.  When vertex markers are on,
            you can move them, delete them
        'd' delete the vertex under point
        'i' insert a vertex at point.  You must be within epsilon of the
            line connecting two existing vertices
    """
    epsilon = 10  # max pixel distance to count as a vertex hit

    def __init__(self, axMan, onselect=None):
        super().__init__(axMan, None)
        self.onselect = onselect
        self.markers = Line2D([0], [0], ls="", marker='o', markerfacecolor='r', animated=True)
        self._ind = None  # the active vert
        self._hoverInd = None
        self.poly = Polygon([[0, 0]], animated=True, facecolor=(0, 1, 0, .1), edgecolor=(0, 0, 1, .9))
        self.addArtist(self.poly)
        self.addArtist(self.markers)
        self.set_visible(False)

    @staticmethod
    def getHelpText():
        return """This Selector will become active after the primary Selector is finished. Click and drag the handle 
        points to adjust the ROI. Press 'd' to delete a point. Press 'i' to insert a new point. Press 'enter' to accept
        the selection."""

    def reset(self):
        pass  # not sure what should be done here.

    def initialize(self, verts):
        """Given a set of points this will initialize the artists to them"""
        x, y = zip(*verts)
        self.markers.set_data(x, y)
        self._interpolate()
        self.set_visible(True)

    def _interpolate(self):
        """update the polygon to match the marker vertices."""
        x, y = self.markers.get_data()
        tck, u = interpolate.splprep([x, y], s=0, per=True)
        # evaluate the spline fits for 1000 evenly spaced distance values
        xi, yi = interpolate.splev(np.linspace(0, 1, 1000), tck)
        self.poly.set_xy(list(zip(xi, yi)))

    def _get_ind_under_point(self, event):
        """get the index of the vertex under point if within epsilon tolerance"""
        # display coords
        xy = np.asarray(list(zip(*self.markers.get_data())))
        xyt = self.markers.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]
        d = np.hypot(xt - event.x, yt - event.y)
        indseq, = np.nonzero(d == d.min())
        ind = indseq[0]
        if d[ind] >= self.epsilon:
            ind = None
        return ind

    def _press(self, event):
        """whenever a mouse button is pressed"""
        if (event.inaxes is None) or (event.button != 1):
            return
        self._ind = self._get_ind_under_point(event)

    def _release(self, event):
        """whenever a mouse button is released"""
        if (event.button != 1):
            return
        self._ind = None

    def _on_key_press(self, event):
        """whenever a key is pressed"""
        #        if not event.inaxes:
        #            return
        if event.key == 'd':
            ind = self._get_ind_under_point(event)
            if ind is not None:
                x, y = self.markers.get_data()
                self.markers.set_data(np.delete(x, ind), np.delete(y, ind))
                self._interpolate()
        elif event.key == 'i':
            xys = list(self.markers.get_transform().transform(np.array(self.markers.get_data()).T))
            p = np.array([event.x, event.y, 0])  # display coords
            d = []
            for i in range(len(xys) - 1):
                s0 = (xys[i][0], xys[i][1], 0)
                s1 = (xys[i + 1][0], xys[i + 1][1], 0)  # Convert to 3d points.
                d.append(pnt2line(p, s0, s1)[0])  # distance from line to click point
            d = np.array(d)
            i = d.argmin()
            if d.min() <= self.epsilon:
                x, y = self.markers.get_data()
                self.markers.set_data(np.insert(x, i + 1, event.xdata), np.insert(y, i + 1, event.ydata))
                self._interpolate()
                print(f"Insert at {i + 1}")
        elif event.key == 'enter':
            self.onselect(self.poly.xy, self.markers.get_data())
            return
        self.axMan.update()

    def _onhover(self, event):
        lastHoverInd = self._hoverInd
        self._hoverInd = self._get_ind_under_point(event)
        if lastHoverInd != self._hoverInd:
            if self._hoverInd is not None:
                self.markers.set_markerfacecolor((0, .9, 1, 1))
            else:
                self.markers.set_markerfacecolor('r')
        self.axMan.update()

    def _ondrag(self, event):
        """on mouse movement"""
        if self._ind is None:
            return
        x, y = event.xdata, event.ydata
        d = list(zip(*self.markers.get_data()))
        d[self._ind] = (x, y)
        if self._ind == 0:
            d[-1] = (x, y)
        elif self._ind == len(d) - 1:
            d[0] = (x, y)
        self.markers.set_data(list(zip(*d)))

        self._interpolate()
        self.axMan.update()

class AdjustableSelector:
    """This class manager an roi selector. By setting `adjustable` true then when the selector calls its `onselect` function
    the results will be passed on to a PolygonInteractor for further tweaking. Tweaking can be confirmed by pressing enter.
    at the end the selector will pass an 2d boolean array and a polygon patch to the `onfinished` function if it has been set."""
    def __init__(self, ax: Axes, image: AxesImage, selectorClass: Type[SelectorWidgetBase], onfinished = None):
        self.axMan = AxManager(ax)
        self.image = image
        self.selector = selectorClass(self.axMan, self.image, onselect=self.goPoly)
        self.selector.active = False
        self.adjuster = PolygonInteractor(self.axMan, onselect=self.finish)
        self.adjuster.active = False
        self.adjustable = False
        self.onfinished = onfinished

    def reset(self):
        self.selector.reset()

    @property
    def adjustable(self):
        return self._adjustable

    @adjustable.setter
    def adjustable(self, enabled: bool):
        self._adjustable = enabled
        if enabled:
            self.selector.onselect = self.goPoly
        else:
            self.selector.onselect = self.finish

    def setActive(self, active: bool):
        if active: #This activates the selector. for a looping selection you should call this method from the onfinished function.
            self.selector.set_active(True)
            self.selector.set_visible(True)
        else:
            self.adjuster.set_active(False)
            self.adjuster.set_visible(False)
            self.selector.set_visible(False)
            self.selector.set_active(False)

    def setSelector(self, selectorClass: Type):
        self.selector.removeArtists()
        self.selector.set_active(False)
        self.selector = selectorClass(self.axMan, self.image)
        self.adjustable = self.adjustable

    def goPoly(self, verts, handles):
        self.selector.set_active(False)
        self.selector.set_visible(False)
        self.adjuster.set_active(True)
        self.adjuster.initialize(handles) # It's important that this happens after `set_active` otherwise we get weird drawing issues

    def finish(self, verts, handles):
        self.setActive(False)
        if self.onfinished is not None:
            self.onfinished(verts)