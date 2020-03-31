"""
==================================================
Compilation (:mod:`pwspy.analysis.compilation`)
==================================================
This module provides objects used during the "Compilation" step of analysis. This is when the data saved during analysis
is combined with ROIs to generate a table of values such as the average RMS, reflectance, diffusion coefficient, etc.

PWS
----------
.. autosummary::
   :toctree: generated/

   PWSAnalysisResults
   PWSCompilerSettings
   PWSRoiCompilationResults
   PWSRoiCompiler

Dynamics
------------
.. autosummary::
    :toctree: generated/

    DynamicsCompilerSettings
    DynamicsRoiCompilationResults
    DynamicsRoiCompiler
    DynamicsAnalysisResults

Generic
--------
.. autosummary::
    :toctree: generated/

    GenericCompilerSettings
    GenericRoiCompilationResults
    GenericRoiCompiler

"""

__all__ = ['DynamicsRoiCompiler', 'DynamicsRoiCompilationResults', 'DynamicsCompilerSettings',
           'PWSRoiCompiler', 'PWSRoiCompilationResults', 'PWSCompilerSettings', 'PWSAnalysisResults',
           'GenericRoiCompiler', 'GenericRoiCompilationResults', 'GenericCompilerSettings']

from ._dynamics import DynamicsCompilerSettings, DynamicsRoiCompilationResults, DynamicsRoiCompiler
from ._pws import PWSAnalysisResults, PWSCompilerSettings, PWSRoiCompilationResults, PWSRoiCompiler
from ._generic import GenericCompilerSettings, GenericRoiCompilationResults, GenericRoiCompiler
