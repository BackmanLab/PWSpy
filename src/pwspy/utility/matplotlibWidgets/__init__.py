"""
Useful classes for interacting with Matplotlib plots. Mostly for the purpose of drawing ROIs.

Selectors
----------
.. autosummary::
   :toctree: generated/

   EllipseSelector
   LassoSelector
   RegionalPaintSelector
   PointSelector

Utility
--------
.. autosummary::
   :toctree: generated/

   AdjustableSelector
   PolygonInteractor
   AxManager

"""
from ._selectorWidgets.adjustableSelector import AdjustableSelector, PolygonInteractor
from ._selectorWidgets.ellipse import EllipseSelector
from ._selectorWidgets.lasso import LassoSelector
from ._selectorWidgets.paint import RegionalPaintSelector
from ._selectorWidgets.point import PointSelector
from .coreClasses import AxManager

__all__ = ['AdjustableSelector', 'PolygonInteractor', 'EllipseSelector', 'LassoSelector', 'RegionalPaintSelector', 'PointSelector', 'AxManager']
