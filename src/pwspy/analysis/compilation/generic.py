from __future__ import annotations
import typing
from dataclasses import dataclass

import numpy as np

from pwspy.dataTypes import Roi
from .abstract import AbstractCompilerSettings, AbstractRoiCompilationResults


@dataclass
class GenericCompilerSettings(AbstractCompilerSettings):
    """These settings determine which values should be processed during compilation"""
    roiArea: bool


@dataclass
class GenericRoiCompilationResults(AbstractRoiCompilationResults):
        """Results for compilation that don't pertain to any specific analysis."""
        roi: Roi
        roiArea: int #the number of pixels of an ROI


class GenericRoiCompiler:
    def __init__(self, settings: GenericCompilerSettings):
        self.settings = settings

    def run(self, roi: Roi) -> GenericRoiCompilationResults:
        if self.settings.roiArea:
            roiArea: typing.Optional[int] = np.sum(roi.mask)
        else:
            roiArea = None

        results = GenericRoiCompilationResults(
                    roi=roi,
                    roiArea=roiArea)
        return results


__all__ = []
