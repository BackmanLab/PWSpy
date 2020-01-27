from ._analysisSettings import PWSAnalysisSettings
from ._analysisResults import PWSAnalysisResults, LegacyPWSAnalysisResults
from ._analysisClass import PWSAnalysis
from typing import Type

__all__ = ['PWSAnalysisSettings', 'PWSAnalysisResults', "LegacyPWSAnalysisResults", "PWSAnalysis", "PWSAnalysisGroup"]

from .._abstract import AbstractAnalysisGroup


class PWSAnalysisGroup(AbstractAnalysisGroup):
    """This class is simply used to group together analysis classes that are compatible with eachother."""
    @staticmethod
    def settingsClass() -> Type[PWSAnalysisSettings]:
        return PWSAnalysisSettings

    @staticmethod
    def resultsClass() -> Type[PWSAnalysisResults]:
        return PWSAnalysisResults

    @staticmethod
    def analysisClass() -> Type[PWSAnalysis]:
        return PWSAnalysis