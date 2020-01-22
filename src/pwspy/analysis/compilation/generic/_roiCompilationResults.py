from __future__ import annotations
from dataclasses import dataclass
import typing

from pwspy.analysis.compilation.abstract import AbstractRoiCompilationResults

if typing.TYPE_CHECKING:
        from pwspy.dataTypes import Roi


@dataclass
class GenericRoiCompilationResults(AbstractRoiCompilationResults):
        """Results for compilation that don't pertain to any specific analysis."""
        roi: Roi
        roiArea: int #the number of pixels of an ROI
