from typing import Tuple, List, Optional

import numpy as np

from pwspy.analysis.compilation.abstract import AbstractRoiCompiler
from pwspy.analysis.compilation.generic import GenericCompilerSettings, GenericRoiCompilationResults
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.dataTypes import Roi
from pwspy.analysis import warnings


class GenericRoiCompiler(AbstractRoiCompiler):
    def __init__(self, settings: GenericCompilerSettings):
        super().__init__(settings)

    def run(self, results: PWSAnalysisResults, roi: Roi) -> Tuple[GenericRoiCompilationResults, List[warnings.AnalysisWarning]]:
        warns = []
        if self.settings.roiArea:
            roiArea: Optional[int] = np.sum(roi.mask)
        else:
            roiArea = None

        results = GenericRoiCompilationResults(
                    roi=roi,
                    roiArea=roiArea)
        warns = [w for w in warns if w is not None]  # Strip None from warns list
        return results, warns