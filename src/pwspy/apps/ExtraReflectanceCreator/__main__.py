import os

from PyQt5.QtWidgets import QApplication, QFileDialog
from pwspy.apps.ExtraReflectanceCreator.ERWorkFlow import ERWorkFlow
import matplotlib.pyplot as plt

from pwspy.apps.ExtraReflectanceCreator.widgets.mainWindow import MainWindow
from pwspy.apps import appPath


class ERApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        plt.interactive(True)
        wDir = QFileDialog.getExistingDirectory(caption='Select Working Directory')
        homeDir = os.path.join(appPath, 'ExtraReflectanceCreatorData')
        if not os.path.exists(homeDir):
            os.mkdir(homeDir)
        self.workflow = ERWorkFlow(wDir, homeDir)
        self.window = MainWindow(self.workflow)


def isIpython():
    try:
        return __IPYTHON__
    except:
        return False

if __name__ == '__main__':
    import sys

    # This prevents errors from happening silently.
    sys.excepthook_backup = sys.excepthook
    def exception_hook(exctype, value, traceback):
        print(exctype, value, traceback)
        sys.excepthook_backup(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook

    if isIpython():
        app = ERApp(sys.argv)
    else:
        print("Not Ipython")
        app = ERApp(sys.argv)
        sys.exit(app.exec_())