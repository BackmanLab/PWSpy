from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Tuple, List, Optional

from pwspy.analysis import warnings
from pwspy.dataTypes import Roi
import typing
if typing.TYPE_CHECKING:
    from ._compilerSettings import AbstractCompilerSettings
    from ._roiCompilationResults import AbstractRoiCompilationResults
    from pwspy.analysis import AbstractAnalysisResults


class AbstractRoiCompiler(ABC):
    def __init__(self, settings: AbstractCompilerSettings):
        self.settings = settings

    @abstractmethod
    def run(self, results: AbstractAnalysisResults, roi: Roi) -> Tuple[AbstractRoiCompilationResults, List[warnings.AnalysisWarning]]:
        pass
