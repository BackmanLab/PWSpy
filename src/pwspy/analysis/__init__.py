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
import enum
from ._abstract import AbstractAnalysisSettings, AbstractAnalysis, AbstractAnalysisResults,\
    AbstractRuntimeAnalysisSettings, AbstractHDFAnalysisResults

# TODO replace slope entirely with CDR

resources = os.path.join(os.path.split(__file__)[0], '_resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')

__all__ = ['AbstractAnalysisSettings', 'AbstractAnalysis', 'AbstractAnalysisResults', "AbstractRuntimeAnalysisSettings",
           'AbstractHDFAnalysisResults', 'resources', 'defaultSettingsPath', 'AnalysisTypes']


@enum.unique
class AnalysisTypes(enum.Enum):
    """An Enumeration used to keep track of the possible analysis types. This could probably be done away with."""
    PWS = "pws"
    DYN = "dyn"
