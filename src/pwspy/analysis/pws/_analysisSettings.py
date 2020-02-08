from __future__ import annotations
import dataclasses
from typing import Optional
from pwspy.analysis._abstract import AbstractRuntimeAnalysisSettings
from pwspy.moduleConsts import Material
from pwspy.analysis import AbstractAnalysisSettings
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ERMetadata


@dataclasses.dataclass
class PWSAnalysisSettings(AbstractAnalysisSettings):
    """Document me!""" #TODO document
    filterOrder: int
    filterCutoff: float
    polynomialOrder: int
    extraReflectanceId: str
    referenceMaterial: Material
    wavelengthStart: int
    wavelengthStop: int
    skipAdvanced: bool
    autoCorrStopIndex: int
    autoCorrMinSub: bool  # Determines if the autocorrelation should have it's minimum subtracted from it before processing. This is mathematically nonsense but is needed if the autocorrelation has negative values in it.
    numericalAperture: float
    relativeUnits: bool #determines if reflectance (and therefore the other parameters) should be calculated in absolute units of reflectance or just relative to the reflectance of the reference image.

    FileSuffix = 'analysis'  # This is used for saving and loading to json

    def _asDict(self) -> dict:
        d = dataclasses.asdict(self)
        if self.referenceMaterial is None:
            d['referenceMaterial'] = None
        else:
            d['referenceMaterial'] = self.referenceMaterial.name  # Convert from enum to string
        return d

    @classmethod
    def _fromDict(cls, d: dict) -> PWSAnalysisSettings:
        if d['referenceMaterial'] is not None:
            d['referenceMaterial'] = Material[d['referenceMaterial']]  # Convert from string to enum
        return cls(**d)


@dataclasses.dataclass
class PWSRuntimeAnalysisSettings(AbstractRuntimeAnalysisSettings):
    settings: PWSAnalysisSettings
    extraReflectanceMetadata: Optional[ERMetadata]

    def getSaveableSettings(self) -> PWSAnalysisSettings:
        return self.settings
