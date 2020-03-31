"""
==================================
PWSpy Apps (:mod:`pwspy.apps`)
==================================

This package is home to GUI applications related to PWS.

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
