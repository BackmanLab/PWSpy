from __future__ import annotations
import typing
from typing import List, Tuple
from pwspy.analysis import warnings
from pwspy.analysis.dynamics import DynamicsAnalysisResults
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.dataTypes import Roi
from pwspy.analysis.compilation.dynamics import DynamicsRoiCompiler
from pwspy.analysis.compilation.pws import PWSRoiCompiler
from pwspy.analysis.compilation.generic import GenericRoiCompiler
if typing.TYPE_CHECKING:
    from pwspy.analysis.compilation.dynamics import DynamicsCompilerSettings, DynamicsRoiCompilationResults
    from pwspy.analysis.compilation.generic import GenericCompilerSettings, GenericRoiCompilationResults
    from pwspy.analysis.compilation.pws import PWSCompilerSettings, PWSRoiCompilationResults


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
    def __init__(self, pws: PWSAnalysisResults, dyn: DynamicsAnalysisResults):
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
