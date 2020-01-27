from ._analysisClass import DynamicsAnalysis
from ._analysisResults import DynamicsAnalysisResults
from ._analysisSettings import DynamicsAnalysisSettings

__all__ = ['DynamicsAnalysisResults', 'DynamicsAnalysisSettings', 'DynamicsAnalysis', "DynamicsAnalysisGroup"]

from .._abstract import AbstractAnalysisGroup
from typing import Type


class DynamicsAnalysisGroup(AbstractAnalysisGroup):
    """This class is simply used to group together analysis classes that are compatible with eachother."""
    @staticmethod
    def settingsClass() -> Type[DynamicsAnalysisSettings]:
        return DynamicsAnalysisSettings

    @staticmethod
    def resultsClass() -> Type[DynamicsAnalysisResults]:
        return DynamicsAnalysisResults

    @staticmethod
    def analysisClass() -> Type[DynamicsAnalysis]:
        return DynamicsAnalysis
