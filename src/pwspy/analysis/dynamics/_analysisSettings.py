from __future__ import annotations
import dataclasses
from pwspy.analysis import AbstractAnalysisSettings
from pwspy.moduleConsts import Material

@dataclasses.dataclass
class DynamicsAnalysisSettings(AbstractAnalysisSettings):
    # filterOrder: int
    # filterCutoff: float
    # polynomialOrder: int
    extraReflectanceId: str
    referenceMaterial: Material
    # wavelengthStart: int
    # wavelengthStop: int
    # skipAdvanced: bool
    # autoCorrStopIndex: int
    # autoCorrMinSub: bool  # Determines if the autocorrelation should have it's minimum subtracted from it before processing. These is mathematically nonsense but is needed if the autocorrelation has negative values in it.
    numericalAperture: float

    def asDict(self) -> dict:
        d = dataclasses.asdict(self)
        if self.referenceMaterial is None:
            d['referenceMaterial'] = None
        else:
            d['referenceMaterial'] = self.referenceMaterial.name  # Convert from enum to string
        return d

    @classmethod
    def fromDict(cls, d: dict) -> DynamicsAnalysisSettings:
        if d['referenceMaterial'] is not None:
            d['referenceMaterial'] = Material[d['referenceMaterial']]  # Convert from string to enum
        return cls(**d)
