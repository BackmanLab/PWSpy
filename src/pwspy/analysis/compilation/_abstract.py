# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

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
