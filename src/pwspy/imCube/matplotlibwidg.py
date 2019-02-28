# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 22:59:45 2019

@author: Nick
"""

from matplotlib.patches import Polygon
from matplotlib.widgets import _SelectorWidget
from matplotlib.lines import Line2D
import matplotlib as mpl
from matplotlib import path
import matplotlib.pyplot as plt
from scipy import interpolate
from shapely.geometry import LinearRing, Polygon as shapelyPolygon
import numpy as np

class myLasso(_SelectorWidget):
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
    button : List[Int], optional
        A list of integers indicating which mouse buttons should be used for
        rectangle selection. You can also specify a single integer if only a
        single button is desired.  Default is ``None``, which does not limit
        which button can be used.

        Note, typically:

        - 1 = left mouse button
        - 2 = center mouse button (scroll wheel)
        - 3 = right mouse button
    """

    def __init__(self, ax, onselect=None, useblit=True, button=None):
        _SelectorWidget.__init__(self, ax, onselect, useblit=useblit, button=button)

        self.verts = None
        self.polygon = Polygon([[0,0]], facecolor=(0,0,1,.1), animated=True, edgecolor=(0,0,1,.8))
        self.polygon.set_visible(False)
        self.ax.add_patch(self.polygon)
        self.artists = [self.polygon]
        self.set_active(True) #needed for blitting to work
        
    def _press(self, event):
        self.verts = [self._get_data(event)]
        self.set_visible(True)



    def _release(self, event):

        self.disconnect_events()
        if (self.verts is not None) and (self.onselect is not None):
            self.onselect(self.verts)
        self.set_visible(False)
        self.set_active(False)

#            l = shapelyPolygon(LinearRing(self.verts))
#            l = l.buffer(0)
#            l=l.simplify(l.length/2e2, preserve_topology=False)
#            self.polygon.set_xy(l.exterior.coords)
#    
#    #        plt.plot(*list(zip(*list(l.exterior.coords))))
#            
#    #        tck,u = interpolate.splprep([[i[0] for i in self.verts], [i[1] for i in self.verts]], per=True)
#    #        unew = np.linspace(0,1)
#    #        out = interpolate.splev(unew, tck)
#    #        self.ax.plot(out[0],out[1])
#    #        pat = path.Path(self.verts, closed=True)
#    #        newverts = [vert for vert,code in pat.iter_segments(simplify=True)]
#            self.p=PolygonInteractor(self.ax, self.polygon.xy)
#            self.p.setActive(True)
#    #        p.wait()
#            self.set_active(True)
#            self.connect_default_events()
#            self.verts = None
#        self.update()

    def _onmove(self, event):
        if self.verts is None:
            return
        self.verts.append(self._get_data(event))
        self.polygon.set_xy(self.verts)
        self.update()
#            self.canvas.restore_region(self.background)
#            self.ax.draw_artist(self.polygon)
#            self.canvas.blit(self.ax.bbox)


class PolygonInteractor(_SelectorWidget):
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
        super().__init__(ax, None, useblit = True)    

        self.line = Line2D([0],[0], ls="",
                           marker='o', markerfacecolor='r',
                           animated=True)
        self.ax.add_line(self.line)
        self._ind = None  # the active vert
        self._hoverInd = None

        self.line2 = Polygon([[0,0]], animated=True, facecolor=(0,0,1,.1), edgecolor=(0,0,1,.9))
        self.ax.add_patch(self.line2)
        self.artists = [self.line2, self.line]
#        self.set_active(True)
#        self.canvas.draw_idle()
        
    def initialize(self, verts):

        x, y = zip(*verts)
        self.line.set_data(x,y)
        print(self.line.get_data())
        xy=[[0,0],[100,100],[0,100]]
#        xy = self.interpolate()
        self.line2.set_xy(xy)
        self.set_visible(True)
        self.update()
        
    def interpolate(self):
        x,y = self.line.get_data()
        tck, u = interpolate.splprep([x, y], s=0, per=True)   
        # evaluate the spline fits for 1000 evenly spaced distance values
        xi, yi = interpolate.splev(np.linspace(0, 1, 1000), tck)
        return list(zip(xi,yi))

    def get_ind_under_point(self, event):
        'get the index of the vertex under point if within epsilon tolerance'
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

    def _press(self, event):
        'whenever a mouse button is pressed'
        if not self.showverts:
            return
        if event.inaxes is None:
            return
        if event.button != 1:
            return
        self._ind = self.get_ind_under_point(event)

    def _release(self, event):
        'whenever a mouse button is released'
        if not self.showverts:
            return
        if event.button != 1:
            return
        self._ind = None

    def _on_key_press(self, event):
        'whenever a key is pressed'
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
                d = np.linalg.norm(np.cross(s0-s1, s1-p))/np.linalg.norm(s0-s1) #distance from line to click point
                if d <= self.epsilon:
                    self.line.set_data(np.insert(self.line.get_data, i+1, [event.ydata, event.xdata], axis=0))
                    break
        elif event.key == 'enter':
            self.done = True
            self.close()
            return
        if self.line.stale:
            self.canvas.draw_idle()


    def _onmove(self, event):
        'on mouse movement'
        if not self.showverts:
            return
        if event.inaxes is None:
            return
        lastHoverInd = self._hoverInd
        self._hoverInd = self.get_ind_under_point(event)
        if lastHoverInd != self._hoverInd:
            if self._hoverInd is not None:
                self.line.set_markerfacecolor((0,.9,1,1))
            else:
                self.line.set_markerfacecolor('r')
            self.update()
        if self._ind is None:
            return

        if event.button == 1:
            x, y = event.xdata, event.ydata
            d = list(zip(*self.line.get_data()))
            d[self._ind] = (x,y)
            if self._ind == 0:
                d[-1] = (x, y)
            elif self._ind == len(d) - 1:
                d[0] = (x, y)
            self.line.set_data(list(zip(*d)))

            xy = self.interpolate()
            self.line2.set_xy(xy)
            self.update()
            
        
if __name__ == '__main__':

    from pwspy import ImCube

#    a = ImCube.loadAny(r'C:\Users\Nick\Downloads\lctf50msdelay\vf5nodelay\Cell1')
#    a.selectLassoROI()
#    fig,ax = a.plotMean()
    fig, ax = plt.subplots()
    def onselect(verts):
        l = shapelyPolygon(LinearRing(verts))
        l = l.buffer(0)
        l=l.simplify(l.length/2e2, preserve_topology=False)
        
        p.active=True
        p.initialize(l.exterior.coords)
    l = myLasso(ax, onselect=onselect)
    p = PolygonInteractor(ax)
    p.active = False
