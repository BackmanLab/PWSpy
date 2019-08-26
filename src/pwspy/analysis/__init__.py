# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 21:44:31 2019

@author: Nick Anthony
"""
__all__ = ['compilation', 'dynamics', 'Analysis', 'LegacyAnalysis', 'AnalysisResultsLoader', 'AnalysisResultsSaver', 'AnalysisSettings', 'warnings']
import os

from ._analysisSettings import AnalysisSettings
from ._analysisResults import AnalysisResultsSaver, AnalysisResultsLoader
from ._analysisClass import Analysis, LegacyAnalysis


# TODO replace slope entirely with CDR

resources = os.path.join(os.path.split(__file__)[0], '_resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')
