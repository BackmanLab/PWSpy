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

"""A package containing functionality useful for calculation reflections.

Subpackages
-------------

.. autosummary::
    :toctree: generated/

    extraReflectance
    multilayerReflectanceEngine
    reflectanceHelper

Classes
---------

.. autosummary::
   :toctree: generated/

   Material
"""

import enum


@enum.unique
class Material(enum.Enum):
    """
    An enumeration class containing items for the various materials that we can calculate reflectance for.
    """
    Glass = enum.auto()
    Water = enum.auto()
    Air = enum.auto()
    Silicon = enum.auto()
    Oil_1_7 = enum.auto()
    Oil_1_4 = enum.auto()
    Ipa = enum.auto()
    Ethanol = enum.auto()
    ITO = enum.auto()