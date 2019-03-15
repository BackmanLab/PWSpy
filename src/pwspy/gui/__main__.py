import os
import traceback

from . import applicationVars


def isIpython():
    try:
        return __IPYTHON__
    except:
        return False



if __name__ == '__main__':
    from pwspy.gui.analysis import PWSApp
    import sys
    try:
        if isIpython():
            app = PWSApp(sys.argv)
        else:
            print("Not Ipython")
            # app = QApplication(sys.argv)
            # ex = App()
            app = PWSApp(sys.argv)
            sys.exit(app.exec_())
    except Exception as e:
        with open(os.path.join(applicationVars.dataDirectory, 'crashLog.txt'), 'w') as f:
            traceback.print_exc(limit=None, file=f)
            print(f"Error Occurred: Please check {os.path.join(applicationVars.dataDirectory, 'crashLog.txt')}")
        raise e