from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, List

from pwspy.dataTypes import Roi
from .. import AbstractAnalysisResults, warnings


class AbstractRoiCompiler(ABC):
    """Condenses data from analysis results down to more digestible values.

    Args:
        settings: The settings for the compiler.
    """
    def __init__(self, settings: AbstractCompilerSettings):
        self.settings = settings

    @abstractmethod
    def run(self, results: AbstractAnalysisResults, roi: Roi) -> Tuple[AbstractRoiCompilationResults, List[warnings.AnalysisWarning]]:
        """Combine information from analysis results and an ROI to produce values averaged over the ROI.

        Args:
            results: The analysis results to compile.
            roi: The ROI to used to segment out a section of the results.
        """
        pass


class AbstractRoiCompilationResults(ABC):
    """The results produced by the compilation."""
    pass


@dataclass
class AbstractCompilerSettings(ABC):
    """These settings determine which values should be processed during compilation"""
    pass


__all__ = []
