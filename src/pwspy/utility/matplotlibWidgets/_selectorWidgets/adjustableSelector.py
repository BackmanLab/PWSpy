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

from __future__ import annotations
import typing
from matplotlib.axes import Axes
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from scipy import interpolate
import numpy as np
from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._selectorWidgets import SelectorWidgetBase
import math

Vector3 = typing.Tuple[float, float, float]
Point3 = typing.Tuple[float, float, float]


def pnt2line(pnt: Point3, start: Point3, end: Point3) -> typing.Tuple[float, Point3]:
    """
    Given a line with coordinates 'start' and 'end' and the
    coordinates of a point 'pnt' the proc returns the shortest
    distance from pnt to the line and the coordinates of the
    nearest point on the line.

    1  Convert the line segment to a vector ('line_vec').
    2  Create a vector connecting start to pnt ('pnt_vec').
    3  Find the length of the line vector ('line_len').
    4  Convert line_vec to a unit vector ('line_unitvec').
    5  Scale pnt_vec by line_len ('pnt_vec_scaled').
    6  Get the dot product of line_unitvec and pnt_vec_scaled ('t').
    7  Ensure t is in the range 0 to 1.
    8  Use t to get the nearest location on the line to the end
       of vector pnt_vec_scaled ('nearest').
    9  Calculate the distance from nearest to pnt_vec_scaled.
    10 Translate nearest back to the start/end line.
    Malcolm Kesson 16 Dec 2012
    
    Args:
        pnt: A 3d point.
        start: The 3d point indicating the start of a line segment
        end: The 3d point indicating the end of a line segment

    Returns:
        A `tuple` containing:
            dist: The distance from `pnt` to the nearest point on the line
            nearest: The nearest point on the line to `pnt`
    """


    def dot(v, w):
        x, y, z = v
        X, Y, Z = w
        return x * X + y * Y + z * Z

    def length(v: Vector3) -> float:
        """
        Return the length of a 3d vector.

        Args:
            v: A 3d vector.

        Returns:
            The length of the vector.
        """
        x, y, z = v
        return math.sqrt(x * x + y * y + z * z)

    def vector(b: Point3, e: Point3) -> Vector3:
        """
        Args:
            b: A 3d point
            e: Another 3d point

        Returns:
            A vector giving the difference between `b` and `e`
        """
        x, y, z = b
        X, Y, Z = e
        return (X - x, Y - y, Z - z)

    def unit(v: Vector3) -> Vector3:
        """
        Args:
            v: A 3d vector.

        Returns:
            A unit vector with the same orientation as `v`
        """
        x, y, z = v
        mag = length(v)
        return (x / mag, y / mag, z / mag)

    def distance(p0: Point3, p1: Point3) -> float:
        """
        Args:
            p0: A 3d point
            p1: Another 3d point

        Returns:
            The distance between `p0` and `p1`.
        """
        return length(vector(p0, p1))

    def scale(v: Vector3, sc: float) -> Vector3:
        """
        Args:
            v: A 3d vector
            sc: A scalar

        Returns:
            A vector of `v` * `sc`.
        """
        x, y, z = v
        return (x * sc, y * sc, z * sc)

    def add(v: Vector3, w: Vector3) -> Vector3:
        """
        Args:
            v: A 3d vector
            w: Another 3d vector

        Returns:
            The sum of `v` and `w`
        """
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
    return dist, nearest


class PolygonInteractor(SelectorWidgetBase):
    """
    A polygon editor.
    https://matplotlib.org/gallery/event_handling/poly_editor.html
    Key-bindings:
        'd' delete the vertex under point
        'i' insert a vertex at point.  You must be within epsilon of the
            line connecting two existing vertices

    Args:
        axMan: The manager for a matplotlib `Axes` that you want to interact with.
        onselect: A callback that will be called when the user hits 'enter'. Should have signature (polygonCoords, sparseHandleCoords).

    Attributes:
        epsilon: The pixel distance required to detect a mouse-over event.
    """
    epsilon: int = 10  # max pixel distance to count as a vertex hit

    def __init__(self, axMan: AxManager, onselect: typing.Optional[typing.Callable] = None):
        super().__init__(axMan, None, onselect=onselect)
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
        """Reset the state of the selector so it's ready for a new selection."""
        pass  # I'm not sure what should be done here for this selector.

    def initialize(self, verts: typing.Sequence[typing.Tuple[float, float]]):
        """Given a set of points this will initialize the artists to them.

        Args:
            verts: A sequence of 2d coordinates to intialize the polygon to.
        """
        x, y = zip(*verts)
        self.markers.set_data(x, y)
        self._interpolate()
        self.set_visible(True)

    def _interpolate(self):
        """update the polygon to match the marker vertices with smooth interpolation in between."""
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
        """whenever a mouse button is pressed. Set self._ind to the nearest marker index."""
        if (event.inaxes is None) or (event.button != 1):
            return
        self._ind = self._get_ind_under_point(event)

    def _release(self, event):
        """whenever a mouse button is released. Set self._ind to None."""
        if (event.button != 1):
            return
        self._ind = None

    def _on_key_press(self, event):
        """whenever a key is pressed"""
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
            if d.min() <= (self.epsilon * 5): #The 5 here was decided arbitrarily
                x, y = self.markers.get_data()
                self.markers.set_data(np.insert(x, i + 1, event.xdata), np.insert(y, i + 1, event.ydata))
                self._interpolate()
        elif event.key == 'enter':
            self.onselect(self.poly.xy, self.markers.get_data())
            return
        self.axMan.update()

    def _onhover(self, event):
        """If the mouse hovers near the polygon then change the appearance to indicate that clicking will be registered.
        Unfortunately couldn't find a good way to change only the appearance of the marker handle that was being
        hovered over."""
        lastHoverInd = self._hoverInd
        self._hoverInd = self._get_ind_under_point(event)
        if lastHoverInd != self._hoverInd:
            if self._hoverInd is not None:
                self.markers.set_markerfacecolor((0, .9, 1, 1))
            else:
                self.markers.set_markerfacecolor('r')
        self.axMan.update()

    def _ondrag(self, event):
        """on mouse movement move the selected marker with the mouse and interpolate."""
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
    """This class manages an roi selector. By setting `adjustable` true then when the selector calls its `onselect` function
    the results will be passed on to a PolygonInteractor for further tweaking. Tweaking can be confirmed by pressing enter.
    at the end the selector will pass a set of coordinates to the `onfinished` function if it has been set.

    Args:
        ax: A matplotlib `Axes` to interact with.
        image: A matplotlib `AxesImage`. Some selectors use the data in this image for their selection.
        selectorClass: A class that implements `SelectorWidgetBase`. This will be the intial selector used.
        onfinished: a callback function when the selection finished. The function should accept a single input argument
            which is a list of the 2d coordinated outlining the selected polygon.
    """
    def __init__(self, ax: Axes, image: AxesImage, selectorClass: typing.Type[SelectorWidgetBase],
                 onfinished: typing.Optional[typing.Callable] = None):
        self.axMan = AxManager(ax)
        self.image = image
        self.selector: SelectorWidgetBase = selectorClass(self.axMan, self.image, onselect=self._goPoly)
        self.selector.active = False
        self.adjuster = PolygonInteractor(self.axMan, onselect=self.finish)
        self.adjuster.active = False
        self.adjustable = False
        self.onfinished = onfinished

    def reset(self):
        """Clear all artists used by the selector. :todo: Shouldn't this check if the `adjuster` is active and reset it as well?"""
        self.selector.reset()

    @property
    def adjustable(self) -> bool:
        """Determines whether or not the polygon interactor will be used to adjust the selection at the end of the initial
        selection."""
        return self._adjustable

    @adjustable.setter
    def adjustable(self, enabled: bool):
        self._adjustable = enabled
        if enabled:
            self.selector.onselect = self._goPoly
        else:
            self.selector.onselect = self.finish

    def setActive(self, active: bool):
        """This activates the selector. for a looping selection you should call this method from the onfinished function."""
        if active:
            self.selector.set_active(True)
            self.selector.set_visible(True)
        else:
            self.adjuster.set_active(False)
            self.adjuster.set_visible(False)
            self.selector.set_visible(False)
            self.selector.set_active(False)

    def setSelector(self, selectorClass: typing.Type):
        """Remove the current selector and replace it with a new type of selector.

        Args:
            selectorClass: A class the implements `SelectorWidgetBase`.
        """
        self.selector.removeArtists()
        self.selector.set_active(False)
        self.selector = selectorClass(self.axMan, self.image)
        self.adjustable = self.adjustable

    def _goPoly(self, verts: typing.Sequence[typing.Sequence[float, float]], handles: typing.Sequence[typing.Sequence[float, float]]):
        """This callback is registered with the selectorWidget when we are in adjustable mode. Upon completion of the
        initial selection this callback passes the handles to the polygon adjuster."""
        self.selector.set_active(False)
        self.selector.set_visible(False)
        self.adjuster.set_active(True)
        self.adjuster.initialize(handles) # It's important that this happens after `set_active` otherwise we get weird drawing issues

    def finish(self, verts, handles):
        """This callback is registered with the selectorWidget when we are not in adjustable mode. In adjustable mode it
        is instead registered with the polygon adjuster. It deactivates the class and calls the `onfinished` callback."""
        self.setActive(False)
        if self.onfinished is not None:
            self.onfinished(verts)