# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
import os
import shutil

from PyQt5.QtWidgets import QApplication

from .AnalysisManager import AnalysisManager
from pwspy.analysis import defaultSettingsPath
from .mainWindow import PWSWindow
from . import applicationVars
from glob import glob


class PWSApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self._setupDataDirectories()
        self.window = PWSWindow()
        self.anMan = AnalysisManager(self)
        self.window.runAction.triggered.connect(self.anMan.run)

    @staticmethod
    def _setupDataDirectories():
        if not os.path.exists(applicationVars.dataDirectory):
            os.mkdir(applicationVars.dataDirectory)
        if not os.path.exists(applicationVars.analysisSettingsDirectory):
            os.mkdir(applicationVars.analysisSettingsDirectory)
            settingsFiles = glob(os.path.join(defaultSettingsPath, '*.json'))
            for f in settingsFiles:
                shutil.copyfile(f, os.path.join(applicationVars.analysisSettingsDirectory, os.path.split(f)[-1]))
        if not os.path.exists(applicationVars.extraReflectionDirectory):
            os.mkdir(applicationVars.extraReflectionDirectory)
            with open('readme.txt', 'w') as f:
                f.write("""Extra reflection `data cubes` and an index file are stored on the Backman Lab google drive account.
                Download the index file and and any data cube you plan to use this this folder.""")
        if not os.path.exists(applicationVars.googleDriveAuthPath):
            os.mkdir(applicationVars.googleDriveAuthPath)