# -*- coding: utf-8 -*-
"""
Created on Sun Feb 24 22:59:45 2019

@author: Nick Anthony
"""

import copy

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Ellipse, Rectangle
from matplotlib.widgets import AxesWidget
from scipy import interpolate
from shapely.geometry import LinearRing, Polygon as shapelyPolygon
from typing import Type
from matplotlib.pyplot import  Axes

class AxManager:
    """An object to manage multiple selector tools on a single axes. only one of these should exist per Axes."""
    def __init__(self, ax: Axes):
        self.artists = []
        self.ax = ax
        self.canvas = self.ax.figure.canvas
        self.useblit = self.canvas.supports_blit
        self.canvas.mpl_connect('draw_event', self._update_background)
        self.background = None

    def update(self):
        """Re-render the axes."""
        if not self.ax.get_visible():
            return False
        if self.useblit:
            if self.background is not None:
                self.canvas.restore_region(self.background)
            for artist in self.artists:
                if artist.get_visible():
                    self.ax.draw_artist(artist)
            self.canvas.blit(self.ax.bbox)
        else:
            self.canvas.draw_idle()
        return False

    def draw(self):
        self.canvas.draw_idle()
    
    def _update_background(self, event):
        """force an update of the background"""
        # If you add a call to `ignore` here, you'll want to check edge case:
        # `release` can call a draw event even when `ignore` is True.
        if self.useblit:
            self.background = self.canvas.copy_from_bbox(self.ax.bbox)


class MySelectorWidget(AxesWidget):
    """Base class for other selection widgets in this file. Requires to be managed by an AxManager. Inherited classes
    can implement a number of action handlers like mouse actions and keyboard presses.
    button allows the user to specify which mouse buttons are valid to trigger an event. This can be an int or list of ints.
    state_modifier_keys should be a dict {state: keyName}, the default is {move=' ', clear='escape', square='shift', center='control'}"""
    def __init__(self, axMan: AxManager, button=None, state_modifier_keys=None):
        AxesWidget.__init__(self, axMan.ax)

        self.visible = True
        self.axMan = axMan
        self.artists = []
        self.connect_event('motion_notify_event', self.onmove)
        self.connect_event('button_press_event', self.press)
        self.connect_event('button_release_event', self.release)
        self.connect_event('key_press_event', self.on_key_press)
        self.connect_event('key_release_event', self.on_key_release)
        self.connect_event('scroll_event', self.on_scroll)

        self.state_modifier_keys = dict(move=' ', clear='escape', square='shift', center='control')
        # self.state_modifier_keys.update(state_modifier_keys or {})

        if isinstance(button, int):
            self.validButtons = [button]
        else:
            self.validButtons = button

        # will save the data (position at mouseclick)
        self.eventpress = None
        # will save the data (pos. at mouserelease)
        self.eventrelease = None
        self._prev_event = None
        self.state = set()

    def set_active(self, active):
        AxesWidget.set_active(self, active)
        if active:
            self.axMan._update_background(None)

    def ignore(self, event):
        """return *True* if *event* should be ignored"""
        if not self.active or not self.axMan.ax.get_visible():
            return True
        if not self.canvas.widgetlock.available(self): # If canvas was locked
            return True
        if not hasattr(event, 'button'):
            event.button = None
        if self.validButtons is not None:  # Only do rectangle selection if event was triggered with a desired button
            if event.button not in self.validButtons:
                return True
        if self.eventpress is None: # If no button was pressed yet ignore the event if it was out of the axes
            return event.inaxes != self.ax
        if event.button == self.eventpress.button: # If a button was pressed, check if the release-button is the same.
            return False
        # If a button was pressed, check if the release-button is the same.
        return (event.inaxes != self.ax or event.button != self.eventpress.button)

    def __get_data(self, event):
        """Get the xdata and ydata for event, with limits"""
        if event.xdata is None:
            return None, None
        x0, x1 = self.axMan.ax.get_xbound()
        y0, y1 = self.axMan.ax.get_ybound()
        xdata = max(x0, event.xdata)
        xdata = min(x1, xdata)
        ydata = max(y0, event.ydata)
        ydata = min(y1, ydata)
        return xdata, ydata

    def __clean_event(self, event):
        """Clean up an event
        Use prev event if there is no xdata
        Limit the xdata and ydata to the axes limits
        Set the prev event
        """
        if event.xdata is None:
            event = self._prev_event
        else:
            event = copy.copy(event)
        event.xdata, event.ydata = self.__get_data(event)
        self._prev_event = event
        return event

    def press(self, event):
        """Button press handler and validator"""
        if not self.ignore(event):
            event = self.__clean_event(event)
            self.eventpress = event
            key = event.key or ''
            key = key.replace('ctrl', 'control')
            # move state is locked in on a button press
            if key == self.state_modifier_keys['move']:
                self.state.add('move')
            self._press(event)
            return True
        return False

    def release(self, event):
        """Button release event handler and validator"""
        if not self.ignore(event) and self.eventpress:
            event = self.__clean_event(event)
            self.eventrelease = event
            self._release(event)
            self.eventpress = None
            self.eventrelease = None
            self.state.discard('move')
            return True
        return False

    def onmove(self, event):
        """Cursor move event handler and validator"""
        if not self.ignore(event):
            event = self.__clean_event(event)
            if self.eventpress:
                self._ondrag(event)
            else:
                self._onhover(event)
            return True
        return False

    def on_scroll(self, event):
        """Mouse scroll event handler and validator"""
        if not self.ignore(event):
            self._on_scroll(event)

    def on_key_press(self, event):
        """Key press event handler and validator for all selection widgets"""
        if self.active:
            key = event.key or ''
            key = key.replace('ctrl', 'control')
            if key == self.state_modifier_keys['clear']:
                self.set_visible(False)
                return
            for (state, modifier) in self.state_modifier_keys.items():
                if modifier in key:
                    self.state.add(state)
            self._on_key_press(event)

    def on_key_release(self, event):
        """Key release event handler and validator"""
        if self.active:
            key = event.key or ''
            for (state, modifier) in self.state_modifier_keys.items():
                if modifier in key:
                    self.state.discard(state)
            self._on_key_release(event)

    def set_visible(self, visible):
        """ Set the visibility of our artists """
        self.visible = visible
        for artist in self.artists:
            artist.set_visible(visible)
        self.axMan.draw()
        
    def addArtist(self, artist):
        """Add a matplotlib artist to be managed."""
        self.axMan.artists.append(artist)
        self.artists.append(artist)
        if isinstance(artist, Patch):
            self.axMan.ax.add_patch(artist)
        elif isinstance(artist, Line2D):
            self.axMan.ax.add_line(artist)
        else:
            self.axMan.ax.add_artist(artist)

    def removeArtists(self):
        for artist in self.artists:
            self.axMan.artists.remove(artist)
            artist.remove()
        self.artists = []
        self.axMan.draw()

    # Overridable events
    def _on_key_release(self, event):
        """Key release event handler"""
        pass
    def _on_key_press(self, event):
        """Key press event handler - use for widget-specific key press actions."""
        pass
    def _on_scroll(self, event):
        """Mouse scroll event handler"""
        pass
    def _ondrag(self, event):
        """Cursor move event handler"""
        pass
    def _onhover(self, event):
        pass
    def _release(self, event):
        """Button release event handler"""
        pass
    def _press(self, event):
        """Button press handler"""
        pass

class MyLasso(MySelectorWidget):
    def __init__(self, axMan: AxManager, onselect=None, button=None):
        super().__init__(axMan, button=button)
        self.onselect = onselect
        self.verts = None
        self.polygon = Polygon([[0,0]], facecolor=(0, 0, 1, .1), animated=True, edgecolor=(0, 0, 1, .8))
        self.polygon.set_visible(False)
        self.addArtist(self.polygon)
#        self.set_active(True) #needed for blitting to work
        
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


class MyEllipse(MySelectorWidget):
    def __init__(self, axMan: AxManager, onselect=None):
        super().__init__(axMan)
        self.started = False
        self.onselect = onselect
        self.settingWidth = False
        self.startPoint = None
        self.patch = Ellipse((0, 0), 0, 0, 0, facecolor=(0, 0, 1, .1), animated=True, edgecolor=(0,0,1,.8))
        self.addArtist(self.patch)

    def _press(self, event):
        if event.button!=1:
            return
        if not self.started:
            self.startPoint = [event.xdata, event.ydata]
            self.patch.set_center(self.startPoint)
            self.started = True
    def _ondrag(self,event):
        if self.started:
            dx = event.xdata-self.startPoint[0]
            dy = event.ydata-self.startPoint[1]
            self.patch.height = np.sqrt(dx**2 + dy**2)
            self.patch.width = self.patch.height / 4
            self.patch.set_center([self.startPoint[0]+dx/2, self.startPoint[1]+dy/2])
            self.patch.angle = np.degrees(np.arctan2(dy,dx)) - 90
            self.axMan.update()
    def _onhover(self, event):
        if self.started:
            dx = event.xdata - self.patch.center[0]
            dy = event.ydata - self.patch.center[1]
            h = np.sqrt(dx**2 + dy**2)
            theta = np.arctan2(dy,dx) - np.radians(self.patch.angle)
            self.patch.width = 2*h*np.cos(theta)
            self.axMan.update()
    def _release(self, event):
        if event.button != 1:
            return
        if self.started:
            if not self.settingWidth:
                self.settingWidth = True
            else:
                self.started = False
                self.settingWidth = False
                if self.onselect:
                    angle = np.linspace(0,2*np.pi, num=100)
                    x_ = self.patch.width/2 * np.cos(angle) #unrotated ellipse centered at origin
                    y_ = self.patch.height/2 * np.sin(angle)
                    s = np.sin(np.radians(self.patch.angle))
                    c = np.cos(np.radians(self.patch.angle))
                    x = x_ * c - y_ * s  # rotate ellipse
                    y = x_ * s + y_ * c
                    x += self.patch.center[0] #translate ellipse
                    y += self.patch.center[1]
                    verts = list(zip(x, y))
                    handles = [verts[0], verts[len(verts)//4], verts[len(verts)//2], verts[3*len(verts)//4], verts[0]]
                    self.onselect(verts, handles)

class MyPoint(MySelectorWidget):
    def __init__(self, axMan: AxManager, onselect = None, side: int = 3):
        super().__init__(axMan)
        self.onselect = onselect
        self.side = side
        self.patch = Rectangle((0, 0), 1, 1, facecolor=(1, 0, 0, 0.5), animated=True)
        self.patch.set_visible(False)
        self.ghostPatch = Rectangle((0, 0), 1, 1, facecolor=(1, 0, 0, 0.2), animated=True)
        self.ghostPatch.set_width(self.side)
        self.ghostPatch.set_height(self.side)                                  
        self.addArtist(self.patch)
        self.addArtist(self.ghostPatch)

    def _onhover(self, event):
        self.ghostPatch.set_xy((event.xdata - self.side / 2, event.ydata - self.side / 2))
        self.axMan.update()

    def _press(self, event):
        if event.button != 1:
            return
        self.point = [event.xdata - self.side / 2, event.ydata - self.side / 2]
        self.patch.set_xy(self.point)
        self.patch.set_width(self.side)
        self.patch.set_height(self.side)
        self.patch.set_visible(True)
        if self.onselect:
            x, y = self.patch.get_xy()
            x = [x, x, x + self.side, x + self.side]
            y = [y, y + self.side, y + self.side, y]
            verts = list(zip(x, y))
            handles = verts
            self.onselect(verts, handles)

    def _on_scroll(self, event):
        delta = event.step
        # if event.button == 'down':
        #     delta = -delta
        self.side += delta
        if self.side < 1:
            self.side = 1
        self.ghostPatch.set_width(self.side)
        self.ghostPatch.set_height(self.side)
        self.axMan.update()


class PolygonInteractor(MySelectorWidget):
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
    epsilon = 15  # max pixel distance to count as a vertex hit

    def __init__(self, axMan, onselect = None):
        super().__init__(axMan, None)    
        self.onselect = onselect
        self.markers = Line2D([0], [0], ls="", marker='o', markerfacecolor='r', animated=True)
        self._ind = None  # the active vert
        self._hoverInd = None
        self.poly = Polygon([[0, 0]], animated=True, facecolor=(0, 1, 0, .1), edgecolor=(0, 0, 1, .9))
        self.addArtist(self.poly)
        self.addArtist(self.markers)
        self.set_visible(False)
        
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
        if (not self.showverts) or (event.inaxes is None) or (event.button != 1):
            return
        self._ind = self._get_ind_under_point(event)

    def _release(self, event):
        """whenever a mouse button is released"""
        if (not self.showverts) or (event.button != 1):
            return
        self._ind = None

    def _on_key_press(self, event):
        """whenever a key is pressed"""
#        if not event.inaxes:
#            return
        if event.key == 't':
            self.showverts = not self.showverts
            self.markers.set_visible(self.showverts)
            if not self.showverts:
                self._ind = None
        elif event.key == 'd':
            ind = self._get_ind_under_point(event)
            if ind is not None:
                x, y = self.markers.get_data()
                self.markers.set_data(np.delete(x, ind), np.delete(y, ind))
                self._interpolate()
        elif event.key == 'i':
            xys = list(self.markers.get_transform().transform(np.array(self.markers.get_data()).T))
            p = np.array([event.x, event.y])  # display coords
            for i in range(len(xys) - 1):
                s0 = xys[i]
                s1 = xys[i + 1]
                d = np.linalg.norm(np.cross(s0-s1, s1-p))/np.linalg.norm(s0-s1) #distance from line to click point
                if d <= self.epsilon:
                    x, y = self.markers.get_data()
                    self.markers.set_data(np.insert(x, i + 1, event.xdata), np.insert(y, i + 1, event.ydata))
                    self._interpolate()
                    print(f"Insert at {i+1}")
                    break
            print("No Insert")
        elif event.key == 'enter':
            self.onselect(self.poly.xy, self.markers.get_data())
            return
        self.axMan.update()

    def _onhover(self, event):
        lastHoverInd = self._hoverInd
        self._hoverInd = self._get_ind_under_point(event)
        if lastHoverInd != self._hoverInd:
            print(f"Hover {self._hoverInd}")
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
    def __init__(self, ax: Axes, selectorClass: Type[MySelectorWidget], onfinished = None):
        self.axMan = AxManager(ax)
        self.selector = selectorClass(self.axMan, onselect=self.goPoly)
        self.selector.active = False
        self.adjuster = PolygonInteractor(self.axMan, onselect=self.finish)
        self.adjuster.active = False
        self.adjustable = False
        self.onfinished = onfinished

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
            self.selector.active = True
            self.selector.set_visible(True)
        else:
            self.adjuster.active = False
            self.adjuster.set_visible(False)
            self.selector.set_visible(False)
            self.selector.active = False

    def setSelector(self, selectorClass: Type):
        self.selector.removeArtists()
        self.selector = selectorClass(self.axMan)
        self.adjustable = self.adjustable

    def goPoly(self, verts, handles):
        self.selector.active = False
        self.selector.set_visible(False)
        self.adjuster.initialize(handles)
        self.adjuster.active = True

    def finish(self, verts, handles):
        self.setActive(False)
        if self.onfinished is not None:
            self.onfinished(verts)

        
if __name__ == '__main__':

    fig, ax = plt.subplots()
    ax.set_aspect('equal')

    a= AdjustableSelector(ax, MyEllipse)
    # a = AdjustableSelector(ax, MyLasso)
    plt.show()
