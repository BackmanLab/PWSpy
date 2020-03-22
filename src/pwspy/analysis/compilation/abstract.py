from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple, List

from pwspy.dataTypes import Roi
from .. import AbstractAnalysisResults, warnings


class AbstractRoiCompiler(ABC):
    def __init__(self, settings: AbstractCompilerSettings):
        self.settings = settings

    @abstractmethod
    def run(self, results: AbstractAnalysisResults, roi: Roi) -> Tuple[AbstractRoiCompilationResults, List[warnings.AnalysisWarning]]:
        pass


class AbstractRoiCompilationResults(ABC):
        pass


@dataclass
class AbstractCompilerSettings(ABC):
    """These settings determine which values should be processed during compilation"""
    pass


__all__ = []
