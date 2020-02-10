# -*- coding: utf-8 -*-
"""
Created on Tue Aug  7 13:20:25 2018

@author: Nick Anthony
"""
import os

__author__ = 'Nick Anthony'
with open(os.path.join(os.path.split(__file__)[0], '_version'), 'r') as f: # We load the version string from a text file. This allows us to easily set the contents of the text file with a build script.
    __version__ = str(f.readline())
