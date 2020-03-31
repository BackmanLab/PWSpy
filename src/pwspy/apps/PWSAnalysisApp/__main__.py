import os
import traceback

from PyQt5.QtWidgets import QApplication
from PyQt5 import QtCore

from pwspy.apps.PWSAnalysisApp.App import PWSApp
from pwspy.apps.PWSAnalysisApp import applicationVars
from datetime import datetime
from pwspy import dateTimeFormat


def main(): #TODO add logging since terminal isn't always available
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

    try:
        if isIpython():  # IPython runs its own QApplication so we handle things slightly different.
            app = PWSApp(sys.argv)
        else:
            print("Starting setup")
            os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1" #TODO replace these options with proper high dpi handling. no pixel specific widths.
            app = PWSApp(sys.argv)
            QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
            print("Application setup complete")
            sys.exit(app.exec_())
    except Exception as e:  # Save error to text file.
        with open(os.path.join(applicationVars.dataDirectory, 'crashLog.txt'), 'a') as f:
            f.writelines([datetime.now().strftime(dateTimeFormat)])
            traceback.print_exc(limit=None, file=f)
            print(f"Error Occurred: Please check {os.path.join(applicationVars.dataDirectory, 'crashLog.txt')}")
        raise e


if __name__ == '__main__':
    main()
