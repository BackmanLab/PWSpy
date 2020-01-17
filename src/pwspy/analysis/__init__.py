# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 21:44:31 2019

@author: Nick Anthony
"""
__all__ = ['compilation', 'dynamics', 'pws', 'warnings', 'AbstractAnalysisSettings', 'AbstractAnalysis', 'AbstractAnalysisResults', 'defaultSettingsPath']
import os
from . import compilation, dynamics, pws, warnings
from ._abstract import AbstractAnalysisSettings, AbstractAnalysis, AbstractAnalysisResults

# TODO replace slope entirely with CDR

resources = os.path.join(os.path.split(__file__)[0], '_resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')
