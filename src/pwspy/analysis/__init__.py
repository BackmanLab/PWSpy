# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 21:44:31 2019

@author: Nick Anthony
"""
import os
from enum import Enum

from ._abstract import AbstractAnalysisSettings, AbstractAnalysis, AbstractAnalysisResults, AbstractRuntimeAnalysisSettings

# TODO replace slope entirely with CDR

resources = os.path.join(os.path.split(__file__)[0], '_resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')

__all__ = ['AbstractAnalysisSettings', 'AbstractAnalysis', 'AbstractAnalysisResults', 'resources', 'defaultSettingsPath', 'AnalysisTypes', 'AbstractRuntimeAnalysisSettings']


class AnalysisTypes(Enum):
    PWS = "pws"
    DYN = "dyn"
