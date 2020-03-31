# -*- coding: utf-8 -*-
"""
Contains all code used for the analysis of data acquired with the PWS system.

Submodules
------------

.. autosummary::
    :toctree: generated/

    compilation
    pws
    warnings
    dynamics

.. autoclass:: AnalysisTypes

"""
import os
from enum import Enum
from ._abstract import AbstractAnalysisSettings, AbstractAnalysis, AbstractAnalysisResults,\
    AbstractRuntimeAnalysisSettings, AbstractHDFAnalysisResults, AbstractAnalysisGroup

# TODO replace slope entirely with CDR

resources = os.path.join(os.path.split(__file__)[0], '_resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')

__all__ = ['AbstractAnalysisSettings', 'AbstractAnalysis', 'AbstractAnalysisResults', "AbstractRuntimeAnalysisSettings",
           'AbstractHDFAnalysisResults', 'AbstractAnalysisGroup', 'resources', 'defaultSettingsPath', 'AnalysisTypes']


class AnalysisTypes(Enum):
    PWS = "pws"
    DYN = "dyn"
