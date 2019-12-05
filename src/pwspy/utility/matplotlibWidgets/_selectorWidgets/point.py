from matplotlib.image import AxesImage
from matplotlib.patches import Rectangle

from pwspy.utility.matplotlibWidgets.coreClasses import AxManager
from pwspy.utility.matplotlibWidgets._selectorWidgets import SelectorWidgetBase


class PointSelector(SelectorWidgetBase):
    def __init__(self, axMan: AxManager, image: AxesImage, onselect = None, side: int = 3):
        super().__init__(axMan, image)
        self.onselect = onselect
        self.side = side
        self.patch = Rectangle((0, 0), 1, 1, facecolor=(1, 0, 0, 0.5), animated=True)
        self.patch.set_visible(False)
        self.ghostPatch = Rectangle((0, 0), 1, 1, facecolor=(1, 0, 0, 0.2), animated=True)
        self.ghostPatch.set_width(self.side)
        self.ghostPatch.set_height(self.side)
        self.addArtist(self.patch)
        self.addArtist(self.ghostPatch)

    def reset(self):
        self.patch.set_visible(False)

    @staticmethod
    def getHelpText():
        return "For selecting a single point with radius of `side`."

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