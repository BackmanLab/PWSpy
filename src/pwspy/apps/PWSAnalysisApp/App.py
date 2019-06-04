# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick Anthony
"""
from __future__ import annotations
import os
import shutil

from PyQt5.QtWidgets import QApplication

from pwspy.imCube import ICMetaData
from .dialogs import AnalysisSummaryDisplay, CompilationSummaryDisplay
from pwspy.apps.PWSAnalysisApp.taskManagers.analysisManager import AnalysisManager
from pwspy.apps.PWSAnalysisApp.taskManagers.compilationManager import CompilationManager
from pwspy.analysis import defaultSettingsPath
from .mainWindow import PWSWindow
from . import applicationVars
from . import resources
from .extraReflectionManager.manager import ERManager
from glob import glob
from typing import List, Tuple, Optional
import typing
if typing.TYPE_CHECKING:
    from pwspy.analysis.compilation import RoiCompilationResults
    from pwspy.analysis.warnings import AnalysisWarning

#TODO add tooltips for everything!!!

class PWSApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self._setupDataDirectories()
        self.ERManager = ERManager(applicationVars.extraReflectionDirectory)
        self.window = PWSWindow()
        self.anMan = AnalysisManager(self)
        self.window.runAction.connect(self.anMan.runList)
        self.parallelProcessing: bool = True #Determines if analysis and compilation should be run in parallel or not.
        self.window.parallelAction.toggled.connect(lambda checked: setattr(self, 'parallelProcessing', checked))
        self.anMan.analysisDone.connect(lambda name, settings, warningList: AnalysisSummaryDisplay(self.window, warningList, name, settings))
        self.compMan = CompilationManager(self)
        self.window.resultsTable.compileButton.released.connect(self.compMan.run)
        self.compMan.compilationDone.connect(self.handleCompilationResults)
        self.window.fileDialog.directoryChanged.connect(self.changeDirectory)
        self.workingDirectory = None

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

    def handleCompilationResults(self, inVal: List[Tuple[ICMetaData, List[Tuple[RoiCompilationResults, Optional[List[AnalysisWarning]]]]]]):
        #  Display warnings if necessary.
        warningStructure = []
        for meta, roiList in inVal:
            metaWarnings = []
            for result, warnList in roiList:
                if len(warnList) > 0:
                    metaWarnings.append((result, warnList))
            if len(metaWarnings) > 0:
                warningStructure.append((meta, metaWarnings))
        if len(warningStructure) > 0:
            CompilationSummaryDisplay(self.window, warningStructure)
        #  Display the results on the table
        results = [(meta, result) for meta, roiList in inVal for result, warnings in roiList]
        self.window.resultsTable.clearCompilationResults()
        [self.window.resultsTable.addCompilationResult(r, md) for md, r in results]

    def changeDirectory(self, directory: str, files: List[str]):
        # Load Cells
        self.window.cellSelector.clearCells()
        for i, f in enumerate(files):
            self.window.cellSelector.addCell(f, directory)
        self.workingDirectory = directory
        self.window.cellSelector.updateFilters()
        #Change title
        self.window.setWindowTitle(f'PWS Analysis v2 - {directory}')
        self.workingDirectory = directory
