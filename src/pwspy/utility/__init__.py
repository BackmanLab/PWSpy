# -*- coding: utf-8 -*-
"""This module provides a number of useful subpackages ranging many different topics

Members
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
           'micromanager', 'matplotlibWidgets', 'DConversion']
