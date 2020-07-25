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

from matplotlib.image import AxesImage
from matplotlib.patches import Rectangle

from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._creatorWidgets import CreatorWidgetBase


class PointCreator(CreatorWidgetBase):
    def __init__(self, axMan: AxManager, image: AxesImage, onselect=None, sideLength: int = 3):
        """ A selector widget that facilitates the selection of a single point in an image. If `sideLength` is greater than 1 it will actually be a square region.

        Args:
            axMan (AxManager): An object that manages the re-rendering of the image. A single matplotlib.Axes can have many selector widgets but should only have one AxManager
            image (AxesImage): the matplotlib image object in use.
            onselect (callable): A function that will be executed after the user selects a point.
            sideLength (int): The initial length (in pixels) of the rectangle used to select a point. This can be changed on the fly with the mouse wheel.

        Returns:
            np.ndarray: The 4 XY vertices of the selection square.
        """
        super().__init__(axMan, image)
        self.onselect = onselect
        self.sideLength = sideLength
        self.patch = Rectangle((0, 0), 1, 1, facecolor=(1, 0, 0, 0.5), animated=True)
        self.patch.set_visible(False)
        self.ghostPatch = Rectangle((0, 0), 1, 1, facecolor=(1, 0, 0, 0.2), animated=True)
        self.ghostPatch.set_width(self.sideLength)
        self.ghostPatch.set_height(self.sideLength)
        self.addArtist(self.patch)
        self.addArtist(self.ghostPatch)

    def reset(self):
        self.patch.set_visible(False)

    @staticmethod
    def getHelpText():
        return "For selecting a single point with radius of `side`."

    def _onhover(self, event):
        self.ghostPatch.set_xy((event.xdata - self.sideLength / 2, event.ydata - self.sideLength / 2))
        self.axMan.update()

    def _press(self, event):
        if event.button != 1:
            return
        self.point = [event.xdata - self.sideLength / 2, event.ydata - self.sideLength / 2]
        self.patch.set_xy(self.point)
        self.patch.set_width(self.sideLength)
        self.patch.set_height(self.sideLength)
        self.patch.set_visible(True)
        if self.onselect:
            x, y = self.patch.get_xy()
            x = [x, x, x + self.sideLength, x + self.sideLength]
            y = [y, y + self.sideLength, y + self.sideLength, y]
            verts = list(zip(x, y))
            handles = verts
            self.onselect(verts, handles)

    def _on_scroll(self, event):
        delta = event.step
        # if event.button == 'down':
        #     delta = -delta
        self.sideLength += delta
        if self.sideLength < 1:
            self.sideLength = 1
        self.ghostPatch.set_width(self.sideLength)
        self.ghostPatch.set_height(self.sideLength)
        self.axMan.update()