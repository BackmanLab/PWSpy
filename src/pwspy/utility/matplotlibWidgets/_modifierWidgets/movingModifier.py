import typing
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent, KeyEvent
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from pwspy.utility.matplotlibWidgets import AxManager
from pwspy.utility.matplotlibWidgets._modifierWidgets import ModifierWidgetBase


class MovingModifier(ModifierWidgetBase):
    """This iteractive widget allows translating and rotating multiple polygons"""
    def __init__(self, axMan: AxManager, image: AxesImage = None, onselect: typing.Optional[ModifierWidgetBase.SelectionFunction] = None):
        super().__init__(axMan, image=image, onselect=onselect)
        self.initialPos = None  # The coords where a drag was started

    @staticmethod
    def getHelpText():
        return """Translation/Rotation: Left click and drag to translate the ROI. Right click and drag to rotate. Press 'enter' to accept
        the new location."""

    def initialize(self, setOfVerts: typing.Sequence[ModifierWidgetBase.PolygonCoords]):
        self.removeArtists()
        self.indicatorLine = Line2D([0, 0], [0, 0], color='k', linestyle='dashed')
        self.originalCoords = setOfVerts
        self.affineTransform = np.identity(3)
        self.addArtist(self.indicatorLine)
        self.polygons = []
        for verts in setOfVerts:
            poly = Polygon(verts, facecolor=(.7, .3, 0, 0.1), linewidth=2, linestyle='dotted', edgecolor=(1, 0, 0, 0.9), animated=True)  # Having animated true here helps with rendering.
            self.addArtist(poly)
            self.polygons.append(poly)
        self.set_visible(True)

    def _press(self, event: MouseEvent):
        self.initialPos = (event.xdata, event.ydata)

    def _ondrag(self, event: MouseEvent):
        delta = (event.xdata - self.initialPos[0], event.ydata - self.initialPos[1])  #Difference between current mouse position and initial pos
        if event.button == 1:  # Left click, translate
            self.indicatorLine.set_data([[self.initialPos[0], event.xdata], [self.initialPos[1], event.ydata]])
            self.affineTransform[0, 2] = delta[0]
            self.affineTransform[1, 2] = delta[1]
        elif event.button == 3:  # Right click rotate
            pass
        self._updatePolygons()

    def _on_key_press(self, event: KeyEvent):
        if event.key == 'escape':
            self.initialize(self.originalCoords)

    def _updatePolygons(self):
        for coords, poly in zip(self.originalCoords, self.polygons):
            poly: Polygon
            coords = np.hstack([np.array(coords), np.ones((len(coords), 1))])
            coords = (self.affineTransform @ coords.T).T
            poly.set_xy(coords[:, :2])
        self.axMan.update()

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    fig: Figure
    ax: Axes
    poly = Polygon([[0, 0], [0, 1], [1, 1], [1, 0]])
    poly2 = Polygon([[1, 1], [1, 1.5], [1.5, 1]])
    ax.add_patch(poly)
    ax.add_patch(poly2)
    ax.set_xlim(-1, 2)
    ax.set_ylim(-1, 2)
    axMan = AxManager(ax)
    mod = MovingModifier(axMan, None, None)
    mod.initialize([poly.get_xy(), poly2.get_xy()])
    mod.set_active(True)
    plt.show()