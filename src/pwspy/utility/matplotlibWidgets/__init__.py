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
