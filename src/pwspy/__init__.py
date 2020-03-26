# -*- coding: utf-8 -*-

"""
==================================================
pwspy (:mod:`pwspy`)
==================================================
This module contains variables that are used across the entirety of the pwspy package. `dateTimeFormat` is the
format string used by the datetime module to load and store time stamps in metadata.

Subpackages
------------
.. autosummary::

   analysis
   apps
   dataTypes
   examples
   utility


Attributes
-----------
.. autosummary::

   dateTimeFormat

"""
import os

__author__ = 'Nick Anthony'

try:
    import git
    rootDir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    repo = git.Repo(rootDir)
    version = repo.git.describe('--tags') #Get the output of the command `git describe --tags` serves as a good version number
    with open(os.path.join(rootDir, 'src', 'pwspy', '_version'), 'w') as f: #Overwrite the version file
        f.write(version)
    print(f"Saved version, {version}, to the `_version` file.")
except Exception as e:
    pass
try:
    with open(os.path.join(os.path.split(__file__)[0], '_version'), 'r') as f: # We load the version string from a text file. This allows us to easily set the contents of the text file with a build script.
        __version__ = str(f.readline())
except FileNotFoundError:
    __version__ = "dev"

dateTimeFormat = "%d-%m-%Y %H:%M:%S"
__all__ = ['dateTimeFormat']


