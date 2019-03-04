# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 22:59:45 2019

@author: Nick
"""

from matplotlib.patches import Polygon
from scipy import interpolate
from shapely.geometry import LinearRing, Polygon as shapelyPolygon


class myBase:
    def __init__(self, ax, blit=True):
        self.ax = ax
        self.blit = blit
        self.canvas = ax.figure.canvas
        self.background = None  # self.canvas.copy_from_bbox(self.ax.bbox)
        self.artists = []
        self.connections = []
        self.canvas.mpl_connect('draw_event', self.onDraw)

    #        self.onDraw(None)
    #
    #        self.canvas.draw()

    def update(self):
        if self.blit:
            #            if self.background:
            self.canvas.restore_region(self.background)
            try:
                [self.ax.draw_artist(i) for i in self.artists]
            except Exception as e:
                print(e)
            self.canvas.blit(self.ax.bbox)
        else:
            self.canvas.draw()

    def setActive(self, active: bool):
        if active:
            self.connections = []
            self.connections.append(self.canvas.mpl_connect('button_press_event', self._onPress))
            self.connections.append(self.canvas.mpl_connect('key_press_event', self._onKey))
            self.connections.append(self.canvas.mpl_connect('button_release_event', self._onRelease))
            self.connections.append(self.canvas.mpl_connect('motion_notify_event', self._onMotion))
        else:
            [self.canvas.mpl_disconnect(i) for i in self.connections]
            self.connections = []
        self.update()

    def setVisible(self, visible: bool):
        if visible:
            [i.set_visible(True) for i in self.artists]
        else:
            [i.set_visible(False) for i in self.artists]

    def onDraw(self, event):
        self.background = self.canvas.copy_from_bbox(self.ax.bbox)
        print(self.background)
        [self.ax.draw_artist(i) for i in self.artists]
        # do not need to blit here, this will fire before the screen is
        # updated

    def _onPress(self, event):
        if event.inaxes == self.ax:
            self.onPress(event)

    def _onKey(self, event):
        self.onKey(event)

    def _onRelease(self, event):
        if event.inaxes == self.ax:
            self.onRelease(event)

    def _onMotion(self, event):
        if event.inaxes == self.ax:
            self.onMotion(event)

    def onPress(self, event):
        pass

    def onKey(self, event):
        pass

    def onRelease(self, event):
        pass

    def onMotion(self, event):
        pass


class myLasso(myBase):
    """
    Selection curve of an arbitrary shape.

    For the selector to remain responsive you must keep a reference to it.

    The selected path can be used in conjunction with `~.Path.contains_point`
    to select data points from an image.

    In contrast to `Lasso`, `LassoSelector` is written with an interface
    similar to `RectangleSelector` and `SpanSelector`, and will continue to
    interact with the axes until disconnected.

    Example usage::

        ax = subplot(111)
        ax.plot(x,y)

        def onselect(verts):
            print(verts)
        lasso = LassoSelector(ax, onselect)

    Parameters
    ----------
    ax : :class:`~matplotlib.axes.Axes`
        The parent axes for the widget.
    onselect : function
        Whenever the lasso is released, the *onselect* function is called and
        passed the vertices of the selected path.
    """

    def __init__(self, ax, onselect=None):
        super().__init__(ax)

        self.verts = None
        self.onselect = onselect
        self.polygon = Polygon([[0, 0]], facecolor=(0, 0, 1, .1), animated=True, edgecolor=(0, 0, 1, .8))
        self.polygon.set_visible(False)
        self.ax.add_patch(self.polygon)
        self.artists = [self.polygon]

    def onPress(self, event):
        self.verts = [[event.xdata, event.ydata]]
        self.setVisible(True)

    def onRelease(self, event):
        if (self.verts is not None) and (self.onselect is not None):
            self.onselect(self)  # self.verts)

    #        self.setActive(False)
    #        l = shapelyPolygon(LinearRing(self.verts))
    #        l = l.buffer(0)
    #        l=l.simplify(l.length/2e2, preserve_topology=False)
    #        self.polygon.set_xy(l.exterior.coords)
    #        self.p=PolygonInteractor(self.ax, self.polygon.xy)
    #        self.p.setActive(True)
    #        self.setActive(True)
    #        self.verts = None
    #        self.update()

    def onMotion(self, event):
        if self.verts is None:
            return
        self.verts.append([event.xdata, event.ydata])
        self.polygon.set_xy(self.verts)
        self.update()


import numpy as np
from matplotlib.lines import Line2D


class PolygonInteractor(myBase):
    """
    A polygon editor.
    https://matplotlib.org/gallery/event_handling/poly_editor.html

    Key-bindings

      't' toggle vertex markers on and off.  When vertex markers are on,
          you can move them, delete them

      'd' delete the vertex under point

      'i' insert a vertex at point.  You must be within epsilon of the
          line connecting two existing vertices
    """

    showverts = True
    epsilon = 5  # max pixel distance to count as a vertex hit

    def __init__(self, ax):
        super().__init__(ax)

        self.line = Line2D([0], [0], ls="",
                           marker='o', markerfacecolor='r',
                           animated=True)
        self.ax.add_line(self.line)
        self._ind = None  # the active vert
        self._hoverInd = None

        self.poly = Polygon([[0, 0]], animated=True, facecolor=(0, 0, 1, .1), edgecolor=(0, 0, 1, .9))
        self.ax.add_patch(self.poly)
        self.artists = [self.poly, self.line]
        [i.set_visible(False) for i in self.artists]

    def initialize(self, verts):
        x, y = zip(*verts)
        xy = self.interpolate(x, y)
        self.line.set_data(x, y)
        self.poly.set_xy(xy)
        self.update()

    @staticmethod
    def interpolate(x, y):
        #        x,y = self.line.get_data()
        tck, u = interpolate.splprep([x, y], s=0, per=True)
        # evaluate the spline fits for 1000 evenly spaced distance values
        xi, yi = interpolate.splev(np.linspace(0, 1, 1000), tck)
        return list(zip(xi, yi))

    def get_ind_under_point(self, event):
        """get the index of the vertex under point if within epsilon tolerance"""
        # display coords
        xy = np.asarray(list(zip(*self.line.get_data())))
        xyt = self.line.get_transform().transform(xy)
        xt, yt = xyt[:, 0], xyt[:, 1]
        d = np.hypot(xt - event.x, yt - event.y)
        indseq, = np.nonzero(d == d.min())
        ind = indseq[0]

        if d[ind] >= self.epsilon:
            ind = None

        return ind

    def onPress(self, event):
        """whenever a mouse button is pressed"""
        if not self.showverts:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return
        self._ind = self.get_ind_under_point(event)

    def onRelease(self, event):
        """whenever a mouse button is released"""
        if not self.showverts:
            return
        if event.button != 1:
            return
        self._ind = None

    def onKey(self, event):
        """whenever a key is pressed"""
        #        if not event.inaxes:
        #            return
        if event.key == 't':
            self.showverts = not self.showverts
            self.line.set_visible(self.showverts)
            if not self.showverts:
                self._ind = None
        elif event.key == 'd':
            ind = self.get_ind_under_point(event)
            if ind is not None:
                self.poly.xy = np.delete(self.poly.xy,
                                         ind, axis=0)
                self.line.set_data(zip(*self.poly.xy))
        elif event.key == 'i':
            xys = self.poly.get_transform().transform(self.poly.xy)
            p = np.array([event.x, event.y])  # display coords
            for i in range(len(xys) - 1):
                s0 = xys[i]
                s1 = xys[i + 1]
                d = np.linalg.norm(np.cross(s0 - s1, s1 - p)) / np.linalg.norm(
                    s0 - s1)  # distance from line to click point
                if d <= self.epsilon:
                    self.line.set_data(np.insert(self.line.get_data, i + 1, [event.ydata, event.xdata], axis=0))
                    break
        elif event.key == 'enter':
            return
        if self.line.stale:
            self.canvas.draw_idle()

    def onMotion(self, event):
        """on mouse movement"""
        if not self.showverts:
            return
        if event.inaxes is None:
            return
        lastHoverInd = self._hoverInd
        self._hoverInd = self.get_ind_under_point(event)
        if lastHoverInd != self._hoverInd:
            if self._hoverInd is not None:
                self.line.set_markerfacecolor((0, .9, 1, 1))
            else:
                self.line.set_markerfacecolor('r')
            self.update()
        if self._ind is None:
            return

        if event.button == 1:
            x, y = event.xdata, event.ydata
            d = list(zip(*self.line.get_data()))
            d[self._ind] = (x, y)
            if self._ind == 0:
                d[-1] = (x, y)
            elif self._ind == len(d) - 1:
                d[0] = (x, y)
            self.line.set_data(list(zip(*d)))

            xy = self.interpolate(*self.line.get_data())
            self.poly.set_xy(xy)
            self.update()


if __name__ == '__main__':
    from pwspy import ImCube

    a = ImCube.loadAny(r'C:\Users\Nick\Downloads\lctf50msdelay\vf5nodelay\Cell1')
    #    a.selectLassoROI()
    fig, ax = a.plotMean()
    fig.canvas.draw()


    def onselect(ref):
        ref.setActive(False)
        l2 = shapelyPolygon(LinearRing(ref.verts))
        l2 = l2.buffer(0)
        l2 = l2.simplify(l2.length / 2e2, preserve_topology=False)
        #        self.polygon.set_xy(l.exterior.coords)
        #        print(list(l.exterior.coords))
        p.initialize(l2.exterior.coords)
        p.setActive(True)
        p.setVisible(True)


    #        ref.update()
    #    l=Lasso(ax,[0,0])
    l = myLasso(ax, onselect=onselect)
    p = PolygonInteractor(ax)
    #
    #    l.setActive(False)
    l.setActive(True)
#    fig.show()
