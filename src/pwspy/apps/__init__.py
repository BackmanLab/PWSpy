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
GUI applications related to PWS.

PWSAnalysisApp
----------------

The main application used for the analysis of PWS and related data.

ExtraReflectanceCreator
-------------------------

This application is used to generate `ExtraReflectanceCube` calibration files and upload them to google drive.

"""

__all__ = ['resources', 'appPath']
import os

resources = os.path.join(os.path.split(__file__)[0], '_resources')

appPath = os.path.expanduser('~/PwspyApps') # Create a directory to store all application data
if not os.path.exists(appPath):
    os.mkdir(appPath)
