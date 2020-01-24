from __future__ import annotations
import numpy as np
from pwspy.dataTypes import Roi
import typing
if typing.TYPE_CHECKING:
    from pwspy.analysis.compilation.generic import GenericCompilerSettings, GenericRoiCompilationResults


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