from __future__ import annotations
from typing import Tuple, List, Optional

import numpy as np

from pwspy.analysis.compilation.abstract import AbstractRoiCompiler
from ._roiCompilationResults import DynamicsRoiCompilationResults
import typing
if typing.TYPE_CHECKING:
    from pwspy.analysis.compilation.dynamics import DynamicsCompilerSettings
    from pwspy.analysis.dynamics import DynamicsAnalysisResults
    from pwspy.dataTypes import Roi
    from pwspy.analysis import warnings


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
