from __future__ import annotations
import typing
from abc import ABCMeta, abstractmethod
from matplotlib.image import AxesImage
from pwspy.utility.matplotlibWidgets.widgetBase import InteractiveWidgetBase
if typing.TYPE_CHECKING:
    from pwspy.utility.matplotlibWidgets import AxManager


class ModifierWidgetBase(InteractiveWidgetBase, metaclass=ABCMeta):
    """This is a base class for interactive widgets that accept a polygon and then produce a new polygon (i.e. modifying the shape).
    Multiple polygons may be modified at once."""

    """Base class for other selection widgets in this package. These widgets are used to create a polygon region from scratch. Requires to be managed by an AxManager. Inherited classes
     can implement a number of action handlers like mouse actions and keyboard presses.

     Args:
         axMan: A reference to the `AxManager` object used to manage drawing the matplotlib `Axes` that this selector widget is active on.
         image: A reference to a matplotlib `AxesImage`. Selectors may use this reference to get information such as data values from the image
             for computer vision related tasks.
         onselect: A callback function that will be called when the selector finishes a selection. See the `onselect` method
            for the appropriate signature.

     Attributes:
         state (set): A `set` that stores strings indicating the current state (Are we dragging the mouse, is the shift
             key pressed, etc.
         artists (list): A `list` of matplotlib widgets managed by the selector.
         axMan (AxManager): The manager for the Axes. Call its `update` method when something needs to be drawn.
         image (AxesImage): A reference to the image being interacted with. Can be used to get the image data.
     """
    def __init__(self, axMan: AxManager, image: typing.Optional[AxesImage] = None,
                 onselect: typing.Optional[typing.Callable] = None):
        super().__init__(axMan, image)
        self._onselect = onselect

    @abstractmethod
    def initialize(self, setOfVerts: typing.Sequence[typing.Sequence[typing.Tuple[float, float]]]):
        """Given a set of points this will initialize the artists to them to begin modification.

        Args:
            setOfVerts: A sequence containing sequences of 2d coordinates to initialize a polygon to. The reason we have
            a sequence of sequences is that multiple polygons can be supported.
        """
        pass

    @staticmethod
    @abstractmethod
    def getHelpText():
        """Return a description of the selector which can be used as a tooltip."""
        return "This Selector has no help text."

    def onselect(self, verts: typing.Sequence[typing.Sequence[float, float]], handles: typing.Sequence[typing.Sequence[float, float]]):  # This method only exists to make the signature of onselect more obvious
        """This method should be called when the interaction is done to execute whatever finalization function was specified
        in the constructor.

        Args:
            verts: A sequence of 2-tuple coordinates that fully define the polygon.
            handles: A reduced sequence of coordinates that define special points onthe shape to potentially be used as draggable handles for a modifier.
        """
        self._onselect(verts, handles)