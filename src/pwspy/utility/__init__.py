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
"""Useful subpackages ranging many different topics

Modules
----------
.. autosummary::
   :toctree: generated/

   GoogleDriveDownloader
   fileIO
   misc
   machineVision
   fluorescence
   plotting
   reflection
   micromanager
   matplotlibWidgets
   DConversion

"""

from ._GoogleDriveDownloader import GoogleDriveDownloader
import os

thinFilmPath = os.path.join(os.path.split(__file__)[0], 'thinFilmInterferenceFiles')

__all__ = ['GoogleDriveDownloader', 'fileIO', 'misc', 'machineVision', 'fluorescence', 'plotting', 'reflection',
           'micromanager', 'DConversion']
