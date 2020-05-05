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

"""
import os
import enum
from ._abstract import AbstractAnalysisSettings, AbstractAnalysis, AbstractAnalysisResults,\
    AbstractRuntimeAnalysisSettings, AbstractHDFAnalysisResults

# TODO replace slope entirely with CDR
# TODO settings are missing reference IDtag but they exists in the results. Results and settings both contain extra reflectance idTag, reduntant

resources = os.path.join(os.path.split(__file__)[0], '_resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')

__all__ = ['AbstractAnalysisSettings', 'AbstractAnalysis', 'AbstractAnalysisResults', "AbstractRuntimeAnalysisSettings",
           'AbstractHDFAnalysisResults', 'resources', 'defaultSettingsPath']

