from __future__ import annotations
from dataclasses import dataclass
from pwspy.analysis.compilation.abstract import AbstractRoiCompilationResults


@dataclass
class DynamicsRoiCompilationResults(AbstractRoiCompilationResults):
    cellIdTag: str
    analysisName: str
    reflectance: float
    rms_t: float
    diffusion: float
