"""
==================================================
Matplotlib Widgets (:mod:`pwspy.utility.matplotlibWidgets`)
==================================================
This module provides a number of useful classes for interacting with Matplotlib plots.

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
