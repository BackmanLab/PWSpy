# -*- coding: utf-8 -*-
"""
This module contains variables that are used across the entirety of the pwspy package. `dateTimeFormat` is the
format string used by the datetime module to load and store time stamps in metadata.
"""
from . import version

__author__ = 'Nick Anthony'

__version__ = version.pwspyVersion

dateTimeFormat = "%d-%m-%Y %H:%M:%S"
__all__ = ['dateTimeFormat']


