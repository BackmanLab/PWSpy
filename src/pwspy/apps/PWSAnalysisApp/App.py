# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick
"""
from __future__ import annotations
import os
import shutil

from PyQt5.QtWidgets import QApplication
from .dialogs import AnalysisSummaryDisplay
from .AnalysisManager import AnalysisManager
from pwspy.analysis import defaultSettingsPath
from .mainWindow import PWSWindow
from . import applicationVars
from . import resources
from .extraReflectionManager.manager import ERManager
from glob import glob

#TODO add progress bar for analysis run

class PWSApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self._setupDataDirectories()
        self.ERManager = ERManager(applicationVars.extraReflectionDirectory)
        self.window = PWSWindow()
        self.anMan = AnalysisManager(self)
        self.window.runAction.triggered.connect(self.anMan.runList)
        self.anMan.analysisDone.connect(lambda name, settings, warningList: AnalysisSummaryDisplay(self.window, name, settings, warningList))

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
            shutil.copyfile(os.path.join(resources, 'credentials.json'), os.path.join(applicationVars.googleDriveAuthPath, 'credentials.json'))

    def loadCells(self, directory, files):
        self.window.cellSelector.clearCells()
        for i, f in enumerate(files):
            self.window.cellSelector.addCell(f, directory)
        self.window.cellSelector.updateFilters()
