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
import typing
from typing import List

from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, QApplication, QSplitter, QTreeWidget, QTreeWidgetItem
import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pwspy.utility.plotting._sharedWidgets import AnimationDlg

#Typing aliases
ArtistCollection = List[Artist]  # A collection of artists that will all be displayed at once.

class MultiPlot(QWidget): #TODO tree view instead of flipping through. add categories.
    """
    A widget that allows the user to flip through a set of matplotlib artists (images, plots, etc.)

    Args:
        artists: A list of lists of matplotlib 'Artists`. each list will comprise a single frame, just like the matplotlib `ArtistAnimation` works.
        title (str): The name for the title of the window
    """
    def __init__(self, artists: typing.Dict[str, ArtistCollection], title: str, parent=None):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        self.setWindowTitle(title)
        self.artists = artists
        self.figure: Figure = artists[0][0].figure  # We are assuming that all artists use the same figure.
        self.ax: Axes = self.artists[0][0].axes

        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus) #Not sure what this is for
        self.canvas.setFocus()

        self.previousButton = QPushButton('←')
        self.nextButton = QPushButton('→')
        self.previousButton.released.connect(self.showPreviousIm)
        self.nextButton.released.connect(self.showNextIm)

        self.saveButton = QPushButton("Save Animation")
        self.saveButton.released.connect(lambda: AnimationDlg(self.figure, self.artists, self).exec())

        imWidg = QWidget()
        layout = QGridLayout()
        layout.addWidget(self.canvas, 0, 0, 8, 8)
        # layout.addWidget(self.previousButton, 9, 1, 1, 1)
        # layout.addWidget(self.nextButton, 9, 2, 1, 1)
        layout.addWidget(self.saveButton, 9, 7, 1, 1)
        layout.addWidget(NavigationToolbar2QT(self.canvas, self), 10, 0, 1, 4)
        layout.setRowStretch(0, 1)  # This causes the plot to take up all the space that isn't needed by the other widgets.
        imWidg.setLayout(layout)

        treeWidg = DictTreeView()

        splitter = QSplitter(self)
        splitter.addWidget(treeWidg)
        splitter.addWidget(imWidg)

        self.setLayout(QGridLayout())
        self.layout().addWidget(splitter)

        self.index = 0
        self._updateDisplayedImage()

    def showPreviousIm(self):
        """Display the previous set of display elements."""
        self.index -= 1
        if self.index < 0:
            self.index = len(self.artists) - 1
        self._updateDisplayedImage()

    def showNextIm(self):
        """Display the next set of display elements."""
        self.index += 1
        if self.index >= len(self.artists):
            self.index = 0
        self._updateDisplayedImage()

    def imshow(self, *args, **kwargs):
        """Mirrors the pyplot.imshow function. Adds a new image to the set of images shown by this widget."""
        self.artists.append([self.ax.imshow(*args, **kwargs)])
        self.index = len(self.artists)-1
        self._updateDisplayedImage()

    def _updateDisplayedImage(self):
        for i, frame in enumerate(self.artists):
            for artist in frame:
                artist.set_visible(self.index==i)
        self.canvas.draw_idle()


class DictTreeView(QTreeWidget):
    def setDict(self, d: dict):
        self.clear()
        self._fillItem(self.invisibleRootItem(), d)

    @staticmethod
    def _fillItem(item: QTreeWidgetItem, value: typing.Union[dict, list]):
        """Recursively populate a tree item with children to match the contents of a `dict`"""
        item.setExpanded(True)
        if isinstance(value, dict):
            for key, val in value.items():
                child = QTreeWidgetItem()
                child.setText(0, f"{key}")
                item.addChild(child)
                if isinstance(val, (list, dict)):
                    DictTreeView._fillItem(child, val)
                else:
                    child.setText(1, f"{val}")
        elif isinstance(value, list):
            for val in value:
                child = QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    DictTreeView._fillItem(child, val)
                elif type(val) is list:
                    child.setText(0, '[list]')
                    DictTreeView._fillItem(child, val)
                else:
                    child.setText(0, val)
                    child.setExpanded(True)


if __name__ == '__main__':
    import sys
    import matplotlib.pyplot as plt
    app = QApplication(sys.argv)
    sh = (1024, 1024)
    ims = [[plt.imshow(np.random.random(sh)), plt.text(100, 100, str(i))] for i in range(3)]
    mp = MultiPlot(ims, "Hey")
    plt.gcf().subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
    mp.ax.get_xaxis().set_visible(False)
    mp.ax.get_yaxis().set_visible(False)
    [mp.imshow(np.random.random(sh)) for i in range(3)]
    mp.show()

    fig, ax = plt.subplots()
    lines = [ax.plot(np.random.random((50,))) for i in range(3)]
    mp2 = MultiPlot(lines, 'Lines')
    mp2.show()

    sys.exit(app.exec())
