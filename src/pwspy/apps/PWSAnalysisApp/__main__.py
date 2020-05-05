import logging
import os
import time
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5 import QtCore

from pwspy.apps.PWSAnalysisApp.App import PWSApp
from pwspy.apps.PWSAnalysisApp import applicationVars
from datetime import datetime
from pwspy import dateTimeFormat


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
