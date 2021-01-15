# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import shutil
from glob import glob
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5 import QtCore
from pwspy.apps.PWSAnalysisApp.App import PWSApp
from pwspy.apps.PWSAnalysisApp import applicationVars
from datetime import datetime
from pwspy.apps.PWSAnalysisApp import resources
from pwspy.analysis import defaultSettingsPath


def _setupDataDirectories():
    if not os.path.exists(applicationVars.dataDirectory):
        os.mkdir(applicationVars.dataDirectory)
    if not os.path.exists(applicationVars.analysisSettingsDirectory):
        os.mkdir(applicationVars.analysisSettingsDirectory)
    settingsFiles = glob(os.path.join(defaultSettingsPath, '*.json'))
    if len(settingsFiles) == 0:
        raise Exception("Warning: Could not find any analysis settings presets.")
    for f in settingsFiles:  # This will overwrite any existing preset files in the application directory with the defaults in the source code.
        shutil.copyfile(f, os.path.join(applicationVars.analysisSettingsDirectory, os.path.split(f)[-1]))
    if not os.path.exists(applicationVars.extraReflectionDirectory):
        os.mkdir(applicationVars.extraReflectionDirectory)
        with open(os.path.join(applicationVars.extraReflectionDirectory, 'readme.txt'), 'w') as f:
            f.write("""Extra reflection `data cubes` and an index file are stored on the Backman Lab google drive account.
            Download the index file and any data cube you plan to use to this folder.""")
        #add an empty index file to avoid crashes if running in offline-mode
        shutil.copyfile(os.path.join(resources, 'index.json'), os.path.join(applicationVars.extraReflectionDirectory, 'index.json'))
    if not os.path.exists(applicationVars.googleDriveAuthPath):
        os.mkdir(applicationVars.googleDriveAuthPath)
        shutil.copyfile(os.path.join(resources, 'credentials.json'),
                        os.path.join(applicationVars.googleDriveAuthPath, 'credentials.json'))


def main():
    import sys
    import getopt

    debugMode = False
    try:
        opts, args = getopt.getopt(sys.argv[1:], '', ['debug'])
        if len(opts) > 0:  # If any arguments were found
            optNames, optVals = zip(*opts)
            if '--debug' in optNames:
                debugMode = True
    except getopt.GetoptError as e:
        print(e)
        sys.exit(1)

    def isIpython():
        try:
            return __IPYTHON__  # Only defined if we are running within ipython
        except NameError:
            return False

    _setupDataDirectories()  # this must happen before the logger can be instantiated
    logger = logging.getLogger('pwspy')  # We use the root logger of the pwspy module so that all loggers in pwspy will be captured.

    # This prevents errors from happening silently. Found on stack overflow.
    sys.excepthook_backup = sys.excepthook
    def exception_hook(exctype, value, traceBack):
        logger.exception("Unhandled Exception! :", exc_info=value, stack_info=True)
        sys.excepthook_backup(exctype, value, traceBack)  # Run the rror through the default exception hook
        sys.exit(1)
    sys.excepthook = exception_hook

    logger.addHandler(logging.StreamHandler(sys.stdout))
    fHandler = logging.FileHandler(os.path.join(applicationVars.dataDirectory, f'log{datetime.now().strftime("%d%m%Y%H%M%S")}.txt'))
    fHandler.setFormatter(logging.Formatter('%(levelname)s: %(asctime)s %(name)s.%(funcName)s(%(lineno)d) - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(fHandler)
    if debugMode:
        logger.setLevel(logging.DEBUG)
        logger.info("Logger set to debug mode.")
    else:
        logger.setLevel(logging.INFO)
        
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"  # TODO replace these options with proper high dpi handling. no pixel specific widths.
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        app = PWSApp(sys.argv)
        #Testing script
        # app.changeDirectory(r'\\backmanlabnas\home\Year3\ethanolTimeSeries\AndrewNUData\+15', False)
        # app.window.cellSelector.setSelectedCells([app.window.cellSelector.getAllCellMetas()[0]])
        # app.window.plots._refreshButton.released.emit()
        # app.window.plots._startRoiDrawing()
        # import qdarkstyle
        # dark_stylesheet = qdarkstyle.load_stylesheet_pyqt5()
        # app.setStyleSheet(dark_stylesheet)

        if not isIpython():  # IPython runs its own QApplication so we handle things slightly different.
            sys.exit(app.exec_())
    except Exception as e:  # Save error to text file.
        logger.exception(e)
        msg = f"Error Occurred. Please check the log in: {applicationVars.dataDirectory}"
        msgBox = QMessageBox.information(None, 'Crash!', msg)
        raise e


if __name__ == '__main__':
    main()
