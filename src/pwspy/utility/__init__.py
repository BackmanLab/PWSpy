# -*- coding: utf-8 -*-
"""
Created on Tue Aug  7 13:20:25 2018

@author: Nick Anthony
"""
__all__ = ['micromanager', 'reflectanceHelper', 'refractiveIndexFiles', 'GoogleDriveDownloader', 'fileIO.py', 'matplotlibwidg', 'misc',
           'PlotNdbackup.py', 'thinFilmInterferenceFiles', 'toD']
from .PlotNd import PlotNd
import os

thinFilmPath = os.path.join(os.path.split(__file__)[0], 'thinFilmInterferenceFiles')
