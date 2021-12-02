# -*- coding: utf-8 -*-
# Copyright 2018-2021 Nick Anthony, Backman Biophotonics Lab, Northwestern University
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
This script saves pws analysis results to the test data. This must be run before many of the other examples will work.
"""

from pwspy import analysis
from pwspy import dataTypes as pwsdt
from examples import PWSExperimentPath

settings = analysis.pws.PWSAnalysisSettings.loadDefaultSettings("Recommended")

# Load our blank reference image which will be used for normalization.
refAcq = pwsdt.Acquisition(PWSExperimentPath / 'Cell3')
ref = refAcq.pws.toDataClass()

anls = analysis.pws.PWSAnalysis(settings=settings, extraReflectance=None, ref=ref)  # Create a new analysis for the given reference image and analysis settings. The "ExtraReflection" calibration is ignored in this case.

acq = pwsdt.Acquisition(PWSExperimentPath / "Cell1")  # Create an "Acquisition" object to handle operations for the data associated with a single acquisition
cube = acq.pws.toDataClass()  # Request that the PWS metadata object load the full data.
results, warnings = anls.run(cube)  # Run the pre-setup analysis on our data. Get the analysis results and potentially a list of warnings from the analysis.

acq.pws.saveAnalysis(results, 'myAnalysis', overwrite=True)  # Save our analysis results to file in the default location alongside the raw data under the `analyses` folder.

loadedResults = acq.pws.loadAnalysis('myAnalysis')  # This is just going to be a copy of `results`, loaded from file.
