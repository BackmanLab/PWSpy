# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

"""
Objects used during the "Compilation" step of analysis. This is when the data saved during analysis
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
           'GenericRoiCompiler', 'GenericRoiCompilationResults', 'GenericCompilerSettings', 'AbstractRoiCompilationResults',
           'AbstractRoiCompiler', 'AbstractCompilerSettings']

from ._dynamics import DynamicsCompilerSettings, DynamicsRoiCompilationResults, DynamicsRoiCompiler
from ._pws import PWSAnalysisResults, PWSCompilerSettings, PWSRoiCompilationResults, PWSRoiCompiler
from ._generic import GenericCompilerSettings, GenericRoiCompilationResults, GenericRoiCompiler
from ._abstract import AbstractCompilerSettings, AbstractRoiCompilationResults, AbstractRoiCompiler
