from abc import ABC
from dataclasses import dataclass


@dataclass
class AbstractCompilerSettings(ABC):
    """These settings determine which values should be processed during compilation"""
    pass
