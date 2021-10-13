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
This is a collection of example usages of the :mod:`pwspy` module.

.. autosummary::
    :toctree: generated/

    flatFieldVisualizer
    limitedOPDSigma
    plotITOThinFilmCalibration
    pwsAnalysis
    ROItoMirror
    syntheticMirror
    findOPDSurface
    roiUsageExample
    opdExampleScript
"""

# Set this to a folder containing multiple "Cell{x}" acquisition folders. Some examples will use this.
PWSExperimentPath = r"C:\Users\backman05\Documents\Bitbucket\pwspython\tests\resources\seqTest"

# Set this to the "Cell{X}" folder of a PWS acquisition. Most of the examples will then refer to this file.
PWSImagePath = r'\\backmanlabnas.myqnapcloud.com\home\Year2\canvassing\Cell868'