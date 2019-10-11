import os
from datetime import datetime

from PyQt5 import QtCore
from PyQt5.QtWidgets import QApplication, QFileDialog, QListWidgetItem
from pwspy.apps.ExtraReflectanceCreator.ERWorkFlow import ERWorkFlow
import matplotlib.pyplot as plt

from pwspy.apps.ExtraReflectanceCreator.widgets.mainWindow import MainWindow
from pwspy.apps import appPath
from pwspy.apps.sharedWidgets.extraReflectionManager import ERManager
import traceback

class ERApp(QApplication):
    def __init__(self, args):
        QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
        super().__init__(args)
        plt.interactive(True)
        settings = QtCore.QSettings("BackmanLab", "ERCreator")
        try:
            initialDir = settings.value('workingDirectory')
        except TypeError: #Setting not found
            initialDir = None
        wDir = QFileDialog.getExistingDirectory(caption='Select the root `ExtraReflection` directory', directory=initialDir)
        settings.setValue("workingDirectory", wDir)
        self.checkDataDir()

        self.workflow = ERWorkFlow(wDir, self.gDriveDir)
        self.erManager = ERManager(self.gDriveDir)
        self.window = MainWindow(self.erManager)
        self.connectWindowToWorkflow()

    def connectWindowToWorkflow(self):
        for k, v in self.workflow.fileStruct.items():
            self.window.listWidg.addItem(k)
        self.window.listWidg.currentItemChanged.connect(self.selectionChanged)
        self.window.deleteFigsButton.released.connect(self.workflow.deleteFigures)
        self.window.saveButton.released.connect(self._cb(lambda: self.workflow.save(self.window.numericalAperture.value())))
        self.window.selListWidg.itemChanged.connect(self.workflow.invalidateCubes)
        self.window.binningCombo.currentIndexChanged.connect(self.workflow.invalidateCubes)
        self.window.compareDatesButton.released.connect(self._cb(self.workflow.compareDates))
        self.window.plotButton.released.connect(
            self._cb(lambda: self.workflow.plot(self.window.numericalAperture.value(), saveToPdf=True, saveDir=self.figsDir)))

    def checkDataDir(self):
        self.homeDir = os.path.join(appPath, 'ExtraReflectanceCreatorData')
        if not os.path.exists(self.homeDir):
            os.mkdir(self.homeDir)
        self.gDriveDir = os.path.join(self.homeDir, 'GoogleDriveData')
        if not os.path.exists(self.gDriveDir):
            os.mkdir(self.gDriveDir)
        self.figsDir = os.path.join(self.homeDir, 'Plots')
        if not os.path.exists(self.figsDir):
            os.mkdir(self.figsDir)

    def loadIfNeeded(self):
        if self.workflow.cubes is None:
            self.workflow.loadCubes(self.window.checkedSettings, self.window.binning)

    def _cb(self, func):
        """Return a wrapped function with extra gui stuff."""
        def newfunc():
            """Toggle button enabled state. load new data if selection has changed. run the callback."""
            try:
                self.window.setEnabled(False)
                self.loadIfNeeded()
                func()
            except:
                traceback.print_exc()
            finally:
                self.window.setEnabled(True)
        return newfunc

    def selectionChanged(self, item: QListWidgetItem, oldItem: QListWidgetItem):
        self.workflow.directoryChanged(item.text())
        self.window.selListWidg.clear()
        settings = set(self.workflow.df['setting'])
        _, settings = zip(*sorted(zip([datetime.strptime(sett, "%m_%d_%Y") for sett in settings], settings)))
        for sett in settings:
            _ = QListWidgetItem(sett)
            _.setFlags(_.flags() | QtCore.Qt.ItemIsUserCheckable)
            _.setCheckState(QtCore.Qt.Unchecked)
            self.window.selListWidg.addItem(_)

def isIpython():
    try:
        return __IPYTHON__
    except:
        return False

if __name__ == '__main__':
    import sys

    # This prevents errors from happening silently.
    sys.excepthook_backup = sys.excepthook
    def exception_hook(exctype, value, tb):
        print(exctype, value, tb)
        sys.excepthook_backup(exctype, value, tb)
        sys.exit(1)
    sys.excepthook = exception_hook

    if isIpython():
        app = ERApp(sys.argv)
    else:
        print("Not Ipython")
        app = ERApp(sys.argv)
        sys.exit(app.exec_())