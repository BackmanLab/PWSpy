from enum import unique, Enum, auto

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
