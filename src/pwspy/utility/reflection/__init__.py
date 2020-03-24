import enum


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