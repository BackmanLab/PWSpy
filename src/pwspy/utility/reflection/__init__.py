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