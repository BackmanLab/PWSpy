# -*- coding: utf-8 -*-
"""
Created on Tue Aug  7 13:20:25 2018

@author: Nick Anthony
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
    import traceback
    traceback.print_exc()
with open(os.path.join(os.path.split(__file__)[0], '_version'), 'r') as f: # We load the version string from a text file. This allows us to easily set the contents of the text file with a build script.
    __version__ = str(f.readline())