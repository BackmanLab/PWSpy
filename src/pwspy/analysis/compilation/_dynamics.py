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
from dataclasses import dataclass
from typing import Tuple, List

import numpy as np

from pwspy.dataTypes import Roi
from ._abstract import AbstractCompilerSettings, AbstractRoiCompilationResults, AbstractRoiCompiler
from .. import warnings
from ..dynamics import DynamicsAnalysisResults


@dataclass
class DynamicsCompilerSettings(AbstractCompilerSettings):
    """These settings determine how a Dynamics acquisition should be compiled."""
    meanReflectance: bool
    rms_t_squared: bool
    diffusion: bool


@dataclass
class DynamicsRoiCompilationResults(AbstractRoiCompilationResults):
    cellIdTag: str
    analysisName: str
    reflectance: float
    rms_t_squared: float
    diffusion: float


class DynamicsRoiCompiler(AbstractRoiCompiler):
    def __init__(self, settings: DynamicsCompilerSettings):
        super().__init__(settings)

    def run(self, results: DynamicsAnalysisResults, roi: Roi) -> Tuple[DynamicsRoiCompilationResults, List[warnings.AnalysisWarning]]:
        reflectance = self._avgOverRoi(roi, results.meanReflectance) if self.settings.meanReflectance else None
        rms_t_squared = self._avgOverRoi(roi, results.rms_t_squared) if self.settings.rms_t_squared else None  # Unlike with diffusion we should not have any nan values for rms_t. If we get nan then something is wrong with the analysis.
        diffusion = self._avgOverRoi(roi, results.diffusion, np.logical_not(np.isnan(results.diffusion))) if self.settings.diffusion else None  # Don't include nan values in the average. Diffusion is expected to have many Nans due to low SNR.

        results = DynamicsRoiCompilationResults(
                    cellIdTag=results.imCubeIdTag,
                    analysisName=results.analysisName,
                    reflectance=reflectance,
                    rms_t_squared=rms_t_squared,
                    diffusion=diffusion)
        warns = []  # Strip None from warns list
        return results, warns

    @staticmethod
    def _avgOverRoi(roi: Roi, arr: np.ndarray, condition: np.ndarray = None) -> float:
        """Returns the average of arr over the ROI.
        if condition is provided then only value of arr where the condition is satisfied are included."""
        assert len(arr.shape) == 2
        if condition is not None:
            return arr[np.logical_and(roi.mask, condition)].mean()
        else:
            return arr[roi.mask].mean()

