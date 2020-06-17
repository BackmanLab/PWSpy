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
import time
import traceback
from glob import glob

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5 import QtCore

from pwspy.apps.PWSAnalysisApp.App import PWSApp
from pwspy.apps.PWSAnalysisApp import applicationVars
from datetime import datetime
from pwspy import dateTimeFormat
from pwspy.apps.PWSAnalysisApp import resources
from pwspy.analysis import defaultSettingsPath
from pwspy.apps.sharedWidgets.extraReflectionManager.ERIndex import ERIndex


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

    def isIpython():
        try:
            return __IPYTHON__
        except:
            return False

    # This prevents errors from happening silently. Found on stack overflow.
    sys.excepthook_backup = sys.excepthook
    def exception_hook(exctype, value, traceBack):
        print(exctype, value, traceBack)
        sys.excepthook_backup(exctype, value, traceBack)
        sys.exit(1)
    sys.excepthook = exception_hook

    _setupDataDirectories() # this must happen before the logger can be instantiated
    logger = logging.getLogger('pwspy') # We use the root logger of the pwspy module so that all loggers in pwspy will be captured.
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    fHandler = logging.FileHandler(os.path.join(applicationVars.dataDirectory, f'log{datetime.now().strftime("%d%m%Y%H%M%S")}.txt'))
    fHandler.setFormatter(logging.Formatter('%(levelname)s: %(asctime)s %(name)s.%(funcName)s(%(lineno)d) - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(fHandler)
    try:
        os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"  # TODO replace these options with proper high dpi handling. no pixel specific widths.
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        if isIpython():  # IPython runs its own QApplication so we handle things slightly different.
            app = PWSApp(sys.argv)
        else:
            app = PWSApp(sys.argv)
            sys.exit(app.exec_())
    except Exception as e:  # Save error to text file.
        logger.exception(e)
        msg = f"Error Occurred. Please check the log in: {applicationVars.dataDirectory}"
        msgBox = QMessageBox.information(None, 'Crash!', msg)
        raise e


if __name__ == '__main__':
    main()
