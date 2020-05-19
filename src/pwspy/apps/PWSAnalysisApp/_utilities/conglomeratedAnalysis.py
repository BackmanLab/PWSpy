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
from typing import List, Tuple, Optional
from pwspy.analysis import warnings
from pwspy.analysis.dynamics import DynamicsAnalysisResults
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.dataTypes import Roi
from pwspy.analysis.compilation import (DynamicsRoiCompiler, DynamicsCompilerSettings, DynamicsRoiCompilationResults,
                                        PWSRoiCompiler, PWSCompilerSettings, PWSRoiCompilationResults,
                                        GenericRoiCompiler, GenericCompilerSettings, GenericRoiCompilationResults)

"""These utility classes are used to conveniently treat analysis objects of different types that belong together as a single object."""


class ConglomerateCompilerSettings:
    def __init__(self, pwsSettings: PWSCompilerSettings, dynSettings: DynamicsCompilerSettings, genSettings: GenericCompilerSettings):
        self.pws = pwsSettings
        self.dyn = dynSettings
        self.generic = genSettings


class ConglomerateCompilerResults:
    def __init__(self, pws: PWSRoiCompilationResults, dyn: DynamicsRoiCompilationResults, gen: GenericRoiCompilationResults):
        self.pws = pws
        self.dyn = dyn
        self.generic = gen


class ConglomerateAnalysisResults:
    def __init__(self, pws: Optional[PWSAnalysisResults], dyn: Optional[DynamicsAnalysisResults]):
        self.pws = pws
        self.dyn = dyn


class ConglomerateCompiler:
    def __init__(self, settings: ConglomerateCompilerSettings):
        self.settings = settings
        self.pws = PWSRoiCompiler(self.settings.pws)
        self.dyn = DynamicsRoiCompiler(self.settings.dyn)
        self.generic = GenericRoiCompiler(self.settings.generic)

    def run(self, results: ConglomerateAnalysisResults, roi: Roi) -> Tuple[ConglomerateCompilerResults, List[warnings.AnalysisWarning]]:
        if results.pws is not None:
            pwsResults, pwsWarnings = self.pws.run(results.pws, roi)
        else:
            pwsResults, pwsWarnings = None, []
        if results.dyn is not None:
            dynResults, dynWarnings = self.dyn.run(results.dyn, roi)
        else:
            dynResults, dynWarnings = None, []
        genResults = self.generic.run(roi)
        return ConglomerateCompilerResults(pwsResults, dynResults, genResults), pwsWarnings + dynWarnings
