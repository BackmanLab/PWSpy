# -*- coding: utf-8 -*-
"""
Created on Sun Feb 10 13:26:58 2019

@author: Nick Anthony
"""
from __future__ import annotations
import os
import shutil

import psutil
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMessageBox, QSplashScreen
from pwspy import __version__ as version
from pwspy.apps.PWSAnalysisApp._utilities import BlinderDialog, RoiConverter
from pwspy.dataTypes import ICMetaData, AcqDir
from ._dockWidgets.ResultsTableDock import ConglomerateCompilerResults
from .dialogs import AnalysisSummaryDisplay, CompilationSummaryDisplay
from ._taskManagers.analysisManager import AnalysisManager
from ._taskManagers.compilationManager import CompilationManager
from pwspy.analysis import defaultSettingsPath
from .mainWindow import PWSWindow
from . import applicationVars
from . import resources
from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
from glob import glob
from typing import List, Tuple, Optional
import typing
if typing.TYPE_CHECKING:
    from pwspy.analysis.warnings import AnalysisWarning


#TODO sometimes analysisResults will claim access to a file and then we aren't able to delete those files when trying to overwrite with a new analysis.
class PWSApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.setApplicationName(f"PWS Analysis v{version.split('-')[0]}")
        splash = QSplashScreen(QPixmap(os.path.join(resources, 'pwsLogo.png')))
        splash.show()
        self._setupDataDirectories()
        self.ERManager = ERManager(applicationVars.extraReflectionDirectory)
        self.window = PWSWindow(self.ERManager)
        splash.finish(self.window)
        self.anMan = AnalysisManager(self)
        self.window.runAction.connect(self.anMan.runList)
        availableRamGigs = psutil.virtual_memory().available / 1024**3
        if availableRamGigs > 16:  # Default to parallel analysis if we have more than 16 Gb of ram available.
            self.parallelProcessing = True  # Determines if analysis and compilation should be run in parallel or not.
        else:
            self.parallelProcessing = False  # Determines if analysis and compilation should be run in parallel or not.
        self.window.parallelAction.setChecked(self.parallelProcessing)
        self.window.parallelAction.toggled.connect(lambda checked: setattr(self, 'parallelProcessing', checked))
        print(f"Initializing with useParallel set to {self.parallelProcessing}.")
        self.anMan.analysisDone.connect(lambda name, settings, warningList: AnalysisSummaryDisplay(self.window, warningList, name, settings))
        self.compMan = CompilationManager(self.window)
        self.window.resultsTable.compileButton.released.connect(self.compMan.run)
        self.compMan.compilationDone.connect(self.handleCompilationResults)
        self.window.fileDialog.directoryChanged.connect(self.changeDirectory)
        self.window.blindAction.triggered.connect(self.openBlindingDialog)
        self.window.roiConvertAction.triggered.connect(self.convertRois)
        self.workingDirectory = None

    @staticmethod
    def _setupDataDirectories():
        if not os.path.exists(applicationVars.dataDirectory):
            os.mkdir(applicationVars.dataDirectory)
        if not os.path.exists(applicationVars.analysisSettingsDirectory):
            os.mkdir(applicationVars.analysisSettingsDirectory)
        settingsFiles = glob(os.path.join(defaultSettingsPath, '*.json'))
        if len(settingsFiles) == 0:
            raise Exception("Warning: Could not find any analysis settings presets.")
        for f in settingsFiles:
            shutil.copyfile(f, os.path.join(applicationVars.analysisSettingsDirectory, os.path.split(f)[-1]))
        if not os.path.exists(applicationVars.extraReflectionDirectory):
            os.mkdir(applicationVars.extraReflectionDirectory)
            with open('readme.txt', 'w') as f:
                f.write("""Extra reflection `data cubes` and an index file are stored on the Backman Lab google drive account.
                Download the index file and any data cube you plan to use to this folder.""")
        if not os.path.exists(applicationVars.googleDriveAuthPath):
            os.mkdir(applicationVars.googleDriveAuthPath)
            shutil.copyfile(os.path.join(resources, 'credentials.json'), os.path.join(applicationVars.googleDriveAuthPath, 'credentials.json'))
            # shutil.copyfile(os.path.join(resources, 'driveToken.pickle'), os.path.join(applicationVars.googleDriveAuthPath, 'driveToken.pickle'))

    def handleCompilationResults(self, inVal: List[Tuple[AcqDir, List[Tuple[ConglomerateCompilerResults, Optional[List[AnalysisWarning]]]]]]):
        #  Display warnings if necessary.
        warningStructure = []
        for acq, roiList in inVal:
            metaWarnings = []
            for result, warnList in roiList:
                if len(warnList) > 0:
                    metaWarnings.append((result, warnList))
            if len(metaWarnings) > 0:
                warningStructure.append((acq.pws, metaWarnings))
        if len(warningStructure) > 0:
            CompilationSummaryDisplay(self.window, warningStructure)
        #  Display the results on the table
        results = [(acq, result) for acq, roiList in inVal for result, warnings in roiList]
        self.window.resultsTable.clearCompilationResults()
        [self.window.resultsTable.addCompilationResult(r, acq) for acq, r in results]

    def changeDirectory(self, directory: str, files: List[str]):
        # Load Cells
        self.window.cellSelector.clearCells()
        self.window.cellSelector.addCells(files, directory)
        self.workingDirectory = directory
        self.window.cellSelector.updateFilters()
        #Change title
        self.window.setWindowTitle(f'{QApplication.instance().applicationName()} - {directory}')
        self.workingDirectory = directory

    def openBlindingDialog(self):
        metas = self.window.cellSelector.getSelectedCellMetas()
        if len(metas) == 0:
            QMessageBox.information(self.window, "No Cells Selected", "Please select cells to act upon.")
            return
        dialog = BlinderDialog(self.window, self.workingDirectory, metas)
        dialog.exec()

    def convertRois(self):
        metas = self.window.cellSelector.getSelectedCellMetas()
        if len(metas) == 0:
            QMessageBox.information(self.window, "No Cells Selected", "Please select cells to act upon.")
            return
        rc = RoiConverter(metas)
