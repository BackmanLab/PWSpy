from dataclasses import dataclass

from pwspy.analysis.compilation.abstract import AbstractCompilerSettings


@dataclass
class PWSCompilerSettings(AbstractCompilerSettings):
    """These settings determine which values should be processed during compilation"""
    reflectance: bool
    rms: bool
    polynomialRms: bool
    autoCorrelationSlope: bool
    rSquared: bool
    ld: bool
    opd: bool
    meanSigmaRatio: bool
