from __future__ import annotations
import dataclasses
from pwspy.analysis import AbstractAnalysisSettings
from pwspy.moduleConsts import Material


@dataclasses.dataclass
class DynamicsAnalysisSettings(AbstractAnalysisSettings):
    extraReflectanceId: str
    referenceMaterial: Material
    numericalAperture: float
    relativeUnits: bool

    FileSuffix = "dynAnalysis"

    def _asDict(self) -> dict:
        d = dataclasses.asdict(self)
        if self.referenceMaterial is None:
            d['referenceMaterial'] = None
        else:
            d['referenceMaterial'] = self.referenceMaterial.name  # Convert from enum to string
        return d

    @classmethod
    def _fromDict(cls, d: dict) -> DynamicsAnalysisSettings:
        if d['referenceMaterial'] is not None:
            d['referenceMaterial'] = Material[d['referenceMaterial']]  # Convert from string to enum
        return cls(**d)
