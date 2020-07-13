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
import typing
from dataclasses import dataclass

import numpy as np

from pwspy.dataTypes import Roi
from ._abstract import AbstractCompilerSettings, AbstractRoiCompilationResults


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

