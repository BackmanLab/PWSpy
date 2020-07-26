from matplotlib.image import AxesImage

from pwspy.utility.matplotlibWidgets import AxManager
from pwspy.utility.matplotlibWidgets._modifierWidgets import ModifierWidgetBase


class MovingModifier(ModifierWidgetBase):
    """This iteractive widget allows translating and rotating multiple polygons"""
    def __init__(self, axMan: AxManager, image: AxesImage, onselect: typing.Calla):
        super().__init__(axMan, image=image, onselect=onselect)