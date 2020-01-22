from dataclasses import dataclass

from pwspy.analysis.compilation.abstract import AbstractCompilerSettings


@dataclass
class GenericCompilerSettings(AbstractCompilerSettings):
    """These settings determine which values should be processed during compilation"""
    roiArea: bool
