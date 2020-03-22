import enum

"""This module contains variables that are used across the entirety of the pwspy package. `dateTimeFormat` is the
format string used by the datetime module to load and store time stamps in metadata.
`Material` is an enum.Enum class containing items for the various materials that we can calculate reflectance for."""

dateTimeFormat = "%d-%m-%Y %H:%M:%S"


@enum.unique
class Material(enum.Enum):
    Glass = enum.auto()
    Water = enum.auto()
    Air = enum.auto()
    Silicon = enum.auto()
    Oil_1_7 = enum.auto()
    Oil_1_4 = enum.auto()
    Ipa = enum.auto()
    Ethanol = enum.auto()
    ITO = enum.auto()
