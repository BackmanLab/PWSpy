# -*- coding: utf-8 -*-
"""
Created on Tue Aug  7 13:20:25 2018

@author: Nick Anthony
"""
import os

__author__ = 'Nick Anthony'

versionFile = os.path.join(os.path.split(__file__)[0], '_version')
if os.path.exists(versionFile):  #This is the case for packaged distributions of the code
    with open(versionFile, 'r') as f:  # We load the version string from a text file. This allows us to easily set the contents of the text file with a build script.
        __version__ = str(f.readline())
else:  # When running the code from source we dynamically determine the version from git.
    from git import Repo
    pwspyDir = os.path.dirname(os.path.abspath(__file__))
    srcDir = os.path.split(pwspyDir)[0]
    rootDir = os.path.split(srcDir)[0]
    repo = Repo(rootDir)
    __version__ = repo.git.describe('--tags')
