from __future__ import annotations

from dataclasses import dataclass

from pwspy.analysis.compilation.abstract import AbstractRoiCompilationResults


@dataclass
class DynamicsRoiCompilationResults(AbstractRoiCompilationResults):
        reflectance: float
        rms_t: float