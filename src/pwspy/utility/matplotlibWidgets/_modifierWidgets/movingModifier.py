import typing
import numpy as np
from matplotlib.axes import Axes
from matplotlib.backend_bases import MouseEvent, KeyEvent
from matplotlib.figure import Figure
from matplotlib.image import AxesImage
from matplotlib.lines import Line2D
from matplotlib.patches import Polygon
from matplotlib.text import Text

from pwspy.utility.matplotlibWidgets import AxManager
from pwspy.utility.matplotlibWidgets._modifierWidgets import ModifierWidgetBase


class MovingModifier(ModifierWidgetBase):
    """This iteractive widget allows translating and rotating multiple polygons"""
    def __init__(self, axMan: AxManager, image: AxesImage = None, onselect: typing.Optional[ModifierWidgetBase.SelectionFunction] = None):
        super().__init__(axMan, image=image, onselect=onselect)
        self.initialClickPoint = None  # The coords where a drag was started
        self.indicatorLine = Line2D([0, 0], [0, 0], color='k', linestyle='dashed', animated=True)
        self.angleRefLine = Line2D([0, 0], [0, 0], color='r', animated=True)
        self.angleIndicatorLine = Line2D([0, 0], [0, 0], color='b', animated=True)
        self.transformText = Text(self.axMan.ax.get_xlim()[0], self.axMan.ax.get_ylim()[0], "", animated=True)
        self.addArtist(self.indicatorLine)
        self.addArtist(self.angleRefLine)
        self.addArtist(self.angleIndicatorLine)
        self.addArtist(self.transformText)
        self.setArtistVisible(self.angleIndicatorLine, False)
        self.setArtistVisible(self.angleRefLine, False)
        self.polygonArtists = []

    @staticmethod
    def getHelpText():
        return """Translation/Rotation: Left click and drag to translate the ROI. Shift + left click and drag to rotate. Press 'enter' to accept
        the new location. Press 'esc' to reset."""

    def initialize(self, setOfVerts: typing.Sequence[ModifierWidgetBase.PolygonCoords]):
        [self.removeArtist(artist) for artist in self.polygonArtists]
        self.polygonArtists = []
        self.originalCoords = setOfVerts
        self.affineTransform = np.identity(3)
        self.angle = 0
        self.translation = np.array([0, 0])
        self.initializeRotation = False
        for verts in setOfVerts:
            poly = Polygon(verts, facecolor=(.7, .3, 0, 0.1), linewidth=2, linestyle='dotted', edgecolor=(1, 0, 0, 0.9), animated=True)  # Having animated true here helps with rendering.
            self.addArtist(poly)
            self.polygonArtists.append(poly)
        self.set_visible(True)

    def _press(self, event: MouseEvent):
        self.initialClickPoint = np.array((event.xdata, event.ydata))
        self.initialTranslation = self.translation

    def _ondrag(self, event: MouseEvent):
        mousePoint = np.array((event.xdata, event.ydata))
        span = np.abs(self.axMan.ax.get_xlim()[0] - self.axMan.ax.get_xlim()[1])
        self.lineMagnitude = span / 20  # draw over 1/20th of the view span
        if 'shift' in self.state:
            if self.initializeRotation:
                self.initializeRotation = False
                self._setRotationPoint(mousePoint)
            delta = mousePoint - self.rotationPivotPoint
            self._setRotation(np.arctan2(delta[1], delta[0]))
        else:
            delta = mousePoint - self.initialClickPoint  # Difference between current mouse position and initial pos
            self.indicatorLine.set_data([[self.initialClickPoint[0], event.xdata], [self.initialClickPoint[1], event.ydata]])
            self._setTranslation(self.initialTranslation + delta)
            self._setRotationPoint(mousePoint)

        self.transformText.set_text(f"Trans: ({self.translation[0]:.1f}, {self.translation[1]:.1f})\nRot: {np.degrees(self.angle):.1f} deg.")
        self._updatePolygons()

    def _on_key_press(self, event: KeyEvent):
        if event.key == 'escape':
            self.initialize(self.originalCoords)  # Reset
        elif event.key == 'enter':
            newCoordSet = [poly.get_xy() for poly in self.polygonArtists]
            self.onselect(newCoordSet, newCoordSet)
            self.set_active(False)
        elif event.key == 'shift':  # Begin rotation
            self.initializeRotation = True
            self.setArtistVisible(self.angleRefLine, True)
            self.setArtistVisible(self.angleIndicatorLine, True)

    def _on_key_release(self, event: KeyEvent):
        if event.key == 'shift':  # end rotation
            self.setArtistVisible(self.angleRefLine, False)
            self.setArtistVisible(self.angleIndicatorLine, False)

    def _updatePolygons(self):
        self.affineTransform[0, 2] = self.translation[0]
        self.affineTransform[1, 2] = self.translation[1]
        self.affineTransform[0, 0] = self.affineTransform[1, 1] = np.cos(self.angle)
        self.affineTransform[1, 0] = np.sin(self.angle)
        self.affineTransform[0, 1] = -self.affineTransform[1, 0]
        for coords, poly in zip(self.originalCoords, self.polygonArtists):
            poly: Polygon
            coords = np.array(coords) - (self.rotationPivotPoint - self.translation)  # So that any rotation is centered around our initial click position
            coords = np.hstack([coords, np.ones((len(coords), 1))])
            coords = (self.affineTransform @ coords.T).T
            coords = coords[:, :2] + (self.rotationPivotPoint - self.translation)  # Convert back
            poly.set_xy(coords)
        self.axMan.update()

    def _setRotationPoint(self, point: typing.Tuple[float, float]):
        self.rotationPivotPoint = point
        self.angleRefLine.set_data([point[0], point[0] + self.lineMagnitude], [point[1], point[1]])

    def _setRotation(self, radians: float):
        self.angle = radians
        # self.affineTransform[0, 0] = self.affineTransform[1, 1] = np.cos(self.angle)
        # self.affineTransform[1, 0] = np.sin(self.angle)
        # self.affineTransform[0, 1] = -self.affineTransform[1, 0]
        self.angleIndicatorLine.set_data(
            [self.rotationPivotPoint[0], self.rotationPivotPoint[0] + np.cos(self.angle) * self.lineMagnitude],
            [self.rotationPivotPoint[1], self.rotationPivotPoint[1] + np.sin(self.angle) * self.lineMagnitude])

    def _setTranslation(self, translation: typing.Tuple[float, float]):
        self.translation = translation
        # self.affineTransform[0, 2] = translation[0]
        # self.affineTransform[1, 2] = translation[1]


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