from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton

from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.steps import SequencerStep
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer._ui.TreeView import MyTreeView, DictTreeView
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.sequencerCoordinate import SequencerCoordinateRange


class SequenceViewer(QWidget):
    newCoordSelected = pyqtSignal(SequencerCoordinateRange)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent, QtCore.Qt.Window)
        self.setWindowTitle("Acquisition Sequence Viewer")

        l = QGridLayout()
        self.setLayout(l)

        self._sequenceTree = MyTreeView(self)

        self._showSettingsButton = QPushButton("Show Settings")
        self._showSettingsButton.released.connect(self._showHideSettings)

        self._selectButton = QPushButton("Update Selection")
        def func():
            self._sequenceTree.commitAndClose()
            self.newCoordSelected.emit(self._sequenceTree.getCurrentSelectedCoordinateRange())
            self._selectButton.setEnabled(False)
        self._selectButton.released.connect(func)

        self._settingsTree = DictTreeView()
        self._settingsTree.setColumnCount(2)
        self._settingsTree.setIndentation(10)
        self._sequenceTree.currentItemChanged.connect(lambda item: self._settingsTree.setDict(item.settings))

        self._sequenceTree.newCoordSelected.connect(lambda coordRange: self._selectButton.setEnabled(True))

        l.addWidget(self._sequenceTree, 0, 0)
        l.addWidget(self._selectButton, 1, 0)
        l.addWidget(self._showSettingsButton, 2, 0)
        l.addWidget(self._settingsTree, 0, 1, 1, 3)
        self._settingsTree.hide()

    def setSequenceStepRoot(self, root: SequencerStep):
        self._sequenceTree.setRoot(root)
        self._sequenceTree.expandAll()

    def _showHideSettings(self):
        w = self.width()
        if self._showSettingsButton.text() == "Show Settings":
            self._showSettingsButton.setText("Hide Settings")
            self.setFixedWidth(w*2)
            self._settingsTree.show()
        else:
            self._showSettingsButton.setText("Show Settings")
            self._settingsTree.hide()
            self.setFixedWidth(int(w / 2))