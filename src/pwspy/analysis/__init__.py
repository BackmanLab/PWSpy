# -*- coding: utf-8 -*-
"""
Created on Tue Feb 12 21:44:31 2019

@author: Nick
"""
import os

from .analysisResults import AnalysisResults
from .analysisSettings import AnalysisSettings

# TODO add Dynamics analysis and DynCube

# TODO replace slope entirely with CDR

resources = os.path.join(os.path.split(__file__)[0], 'resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')
