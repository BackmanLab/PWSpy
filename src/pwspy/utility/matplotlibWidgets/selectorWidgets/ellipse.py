import numpy as np
from matplotlib.image import AxesImage
from matplotlib.patches import Ellipse, Circle

from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets.selectorWidgets import SelectorWidgetBase


class EllipseSelector(SelectorWidgetBase):
    def __init__(self, axMan: AxManager, image: AxesImage, onselect=None):
        super().__init__(axMan, image)
        self.started = False
        self.onselect = onselect
        self.settingWidth = False
        self.startPoint = None
        self.patch = Ellipse((0, 0), 0, 0, 0, facecolor=(0, 0, 1, .1), animated=True, edgecolor=(0,0,1,.8))
        self.addArtist(self.patch)
        self.circleGuide = Circle((0, 0), animated=True, edgecolor=(1,0,0,.6), facecolor=(0,0,0,0), linestyle='dotted')
        self.addArtist(self.circleGuide)

    @staticmethod
    def getHelpText():
        return "Click and drag to draw the length of the ellipse. Then click again to set the width."

    def reset(self):
        self.started = False
        self.settingWidth = False
        self.startPoint = None

    def _press(self, event):
        if event.button!=1:
            return
        if not self.started:
            self.startPoint = [event.xdata, event.ydata]
            self.patch.set_center(self.startPoint)
            self.circleGuide.set_center(self.startPoint)
            self.started = True

    def _ondrag(self,event):
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