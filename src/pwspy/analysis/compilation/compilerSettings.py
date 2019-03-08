from dataclasses import dataclass


@dataclass
class CompilerSettings:
    reflectance: bool
    rms: bool
    polynomialRms: bool
    autoCorrelationSlope: bool
    rSquared: bool
    ld: bool
    opd: bool