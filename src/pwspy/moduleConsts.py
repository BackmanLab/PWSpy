from enum import unique, Enum, auto

"""This module contains variables that are used ac ross the entirety of the pwspy package. `dateTimeFormat` is the
format string used by the datetime module to load and store time stamps in metadata.
`Material` is an Enum class containing items for the various materials that we can calculate reflectance for."""

dateTimeFormat = "%d-%m-%Y %H:%M:%S"


@unique
class Material(Enum):
    Glass = auto()
    Water = auto()
    Air = auto()
    Silicon = auto()
    Oil_1_7 = auto()
    Oil_1_4 = auto()
    Ipa = auto()
    Ethanol = auto()
