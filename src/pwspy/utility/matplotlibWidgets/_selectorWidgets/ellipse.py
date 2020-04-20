from __future__ import annotations
import typing
import numpy as np
from matplotlib.image import AxesImage
from matplotlib.patches import Ellipse, Circle

from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._selectorWidgets import SelectorWidgetBase


class EllipseSelector(SelectorWidgetBase):
    """Allows the user to select an elliptical region.

    Args:
        axMan: The manager for a matplotlib `Axes` that you want to interact with.
        image: A reference to a matplotlib `AxesImage`. Selectors may use this reference to get information such as data values from the image
            for computer vision related tasks.
        onselect: A callback that will be called when the user hits 'enter'. Should have signature (polygonCoords, sparseHandleCoords).
    """
    def __init__(self, axMan: AxManager, image: AxesImage, onselect: typing.Callable = None):
        super().__init__(axMan, image, onselect=onselect)
        self.started = False
        self.settingWidth = False
        self.startPoint = None
        self.patch = Ellipse((0, 0), 0, 0, 0, facecolor=(0, 0, 1, .1), animated=True, edgecolor=(0, 0, 1, .8))
        self.addArtist(self.patch)
        self.circleGuide = Circle((0, 0), animated=True, edgecolor=(1, 0, 0, .6), facecolor=(0, 0, 0, 0), linestyle='dotted')
        self.addArtist(self.circleGuide)

    @staticmethod
    def getHelpText():
        """Return a description of the selector which can be used as a tooltip."""
        return "Click and drag to draw the length of the ellipse. Then click again to set the width."

    def reset(self):
        """Reset the state of the selector so it's ready for a new selection."""
        self.started = False
        self.settingWidth = False
        self.startPoint = None

    def _press(self, event):
        """Set the initial point of the selection. Then drag to draw the length of the ellipse."""
        if event.button!=1:
            return
        if not self.started:
            self.startPoint = [event.xdata, event.ydata]
            self.patch.set_center(self.startPoint)
            self.circleGuide.set_center(self.startPoint)
            self.started = True

    def _ondrag(self, event):
        """If an initial point has been selected then draw to draw the length of the ellipse."""
        if self.started:
            dx = event.xdata-self.startPoint[0]
            dy = event.ydata-self.startPoint[1]
            self.patch.height = np.sqrt(dx**2 + dy**2)
            self.patch.width = self.patch.height / 4
            self.patch.set_center([self.startPoint[0]+dx/2, self.startPoint[1]+dy/2])
            self.patch.angle = np.degrees(np.arctan2(dy,dx)) - 90
            self.circleGuide.set_center([self.startPoint[0]+dx/2, self.startPoint[1]+dy/2])
            self.circleGuide.set_radius(np.sqrt(dx**2 + dy**2)/2)
            self.axMan.update()

    def _onhover(self, event):
        if self.started:
            dx = event.xdata - self.patch.center[0]
            dy = event.ydata - self.patch.center[1]
            h = np.sqrt(dx**2 + dy**2)
            theta = np.arctan2(dy, dx) - np.radians(self.patch.angle)
            self.patch.width = 2*h*np.cos(theta)
            self.axMan.update()

    def _release(self, event):
        """If we are drawing the major axis then switch to drawing the second axis. If we are drawing the second axis
        then finalize the selection."""
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