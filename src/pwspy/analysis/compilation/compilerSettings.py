from dataclasses import dataclass


@dataclass
class CompilerSettings:
    """These settings determine which values should be processed during compilation"""
    reflectance: bool
    rms: bool
    polynomialRms: bool
    autoCorrelationSlope: bool
    rSquared: bool
    ld: bool
    opd: bool
    meanSigmaRatio: bool
    roiArea: bool
