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

Inheritance
-------------
.. inheritance-diagram:: pwspy.analysis.pws.PWSAnalysisSettings pwspy.analysis.pws.PWSAnalysisResults pwspy.analysis.pws.PWSAnalysis pwspy.analysis.dynamics.DynamicsAnalysisSettings pwspy.analysis.dynamics.DynamicsAnalysisResults pwspy.analysis.dynamics.DynamicsAnalysis
    :parts: 1

"""
import os
from ._abstract import AbstractAnalysisSettings, AbstractAnalysis, AbstractAnalysisResults, AbstractHDFAnalysisResults
from . import pws
from . import dynamics
from . import compilation
from ._utility import ParallelRunner
# TODO settings are missing reference IDtag but they exist in the results. Results and settings both contain extra reflectance idTag, reduntant

resources = os.path.join(os.path.split(__file__)[0], '_resources')
defaultSettingsPath = os.path.join(resources, 'defaultAnalysisSettings')

__all__ = ['AbstractAnalysisSettings', 'AbstractAnalysis', 'AbstractAnalysisResults',
           'AbstractHDFAnalysisResults', 'resources', 'defaultSettingsPath', 'pws', 'dynamics', 'compilation', 'ParallelRunner']






