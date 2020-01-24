from typing import Tuple, List, Optional

import numpy as np

from pwspy.analysis.compilation.abstract import AbstractRoiCompiler
from pwspy.analysis.compilation.generic import GenericCompilerSettings, GenericRoiCompilationResults
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.dataTypes import Roi
from pwspy.analysis import warnings


class GenericRoiCompiler:
    def __init__(self, settings: GenericCompilerSettings):
        self.settings = settings

    def run(self, roi: Roi) -> GenericRoiCompilationResults:
        if self.settings.roiArea:
            roiArea: Optional[int] = np.sum(roi.mask)
        else:
            roiArea = None

        results = GenericRoiCompilationResults(
                    roi=roi,
                    roiArea=roiArea)
        return results