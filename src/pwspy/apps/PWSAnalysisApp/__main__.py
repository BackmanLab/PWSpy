import os
import traceback

from pwspy.apps.PWSAnalysisApp.App import PWSApp
from pwspy.apps.PWSAnalysisApp import applicationVars


def isIpython():
    try:
        return __IPYTHON__
    except:
        return False



if __name__ == '__main__':
    import sys

    # This prevents errors from happening silently.
    sys.excepthook_backup = sys.excepthook
    def exception_hook(exctype, value, traceBack):
        print(exctype, value, traceBack)
        sys.excepthook_backup(exctype, value, traceBack)
        sys.exit(1)
    sys.excepthook = exception_hook

    try:
        if isIpython():
            app = PWSApp(sys.argv)
        else:
            print("Not Ipython")
            app = PWSApp(sys.argv)
            sys.exit(app.exec_())
    except Exception as e:
        with open(os.path.join(applicationVars.dataDirectory, 'crashLog.txt'), 'w') as f:
            traceback.print_exc(limit=None, file=f)
            print(f"Error Occurred: Please check {os.path.join(applicationVars.dataDirectory, 'crashLog.txt')}")
        raise e
