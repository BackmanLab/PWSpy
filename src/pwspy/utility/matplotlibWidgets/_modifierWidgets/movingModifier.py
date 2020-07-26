import typing

from matplotlib.backend_bases import MouseEvent
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from pwspy.utility.matplotlibWidgets import AxManager
from pwspy.utility.matplotlibWidgets._modifierWidgets import ModifierWidgetBase


class MovingModifier(ModifierWidgetBase):
    """This iteractive widget allows translating and rotating multiple polygons"""
    def __init__(self, axMan: AxManager, image: AxesImage = None, onselect: typing.Optional[ModifierWidgetBase.SelectionFunction] = None):
        super().__init__(axMan, image=image, onselect=onselect)
        self.initialPos = None # The coords where a drag was started

    @staticmethod
    def getHelpText():
        return """Translation/Rotation: Left click and drag to translate the ROI. Right click and drag to rotate. Press 'enter' to accept
        the new location."""

    def initialize(self, setOfVerts: typing.Sequence[ModifierWidgetBase.PolygonCoords]):
        self.removeArtists()
        self.indicatorLine = Line2D([0, 0], [0, 0])
        self.addArtist(self.indicatorLine)
        for verts in setOfVerts:
            poly = Polygon(verts, facecolor=(.7, .3, 0, 0.5), linestyle='dotted', edgecolor=(1, 0, 0, 0.9))
            self.addArtist(poly)
        self.set_visible(True)

    def _press(self, event: MouseEvent):
        self.initialPos = (event.xdata, event.ydata)

    def _ondrag(self, event: MouseEvent):
        delta = (event.xdata - self.initialPos[0], event.ydata - self.initialPos[1])  #Difference between current mouse position and initial pos
        if event.button == 1:  # Left click, translate
            self.indicatorLine.set_data([[self.initialPos[0], event.xdata], [self.initialPos[1], event.ydata]])
        elif event.button == 3:  # Right click rotate
            pass
