from dataclasses import dataclass

import typing

from pwspy.analysis.compilation.abstract import AbstractRoiCompiler

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

class ConglomerateCompiler(AbstractRoiCompiler):
    pass #TODO implement.