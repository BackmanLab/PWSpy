import typing

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QTreeWidget

from pwspy.apps.PWSAnalysisApp.componentInterfaces import CellSelector
from pwspy.apps.PWSAnalysisApp.pluginInterfaces import CellSelectorPlugin
import pwspy.dataTypes as pwsdt
import os

from pwspy.utility.micromanager.pwsseq.pwsSequence import SequencerStep, DictTreeView


def requirePluginActive(method):
    def newMethod(self, *args, **kwargs):
        if self._ui.isVisible():  # If the ui isn't visible then we consider the plugin to be off.
            method(self, *args, **kwargs)
    return newMethod


class AcquisitionSequencerPlugin(CellSelectorPlugin):
    def __init__(self):
        self._selector: CellSelector = None
        self._sequence: SequencerStep = None
        self._cells: typing.List[pwsdt.AcqDir] = None
        self._ui = SequenceViewer()
        self._ui.stepSelectionChanged.connect(self._updateSelectorSelection)

    def setContext(self, selector: CellSelector):
        """set the CellSelector that this plugin is associated to."""
        self._selector = selector

    @requirePluginActive
    def onCellsSelected(self, cells: typing.List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that it has had new cells selected."""
        pass

    @requirePluginActive
    def onReferenceSelected(self, cell: pwsdt.AcqDir):
        """This method will be called when the CellSelector indicates that it has had a new reference selected."""
        pass

    @requirePluginActive
    def onNewCellsLoaded(self, cells: typing.List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that new cells have been loaded to the selector."""
        #Search the parent directory for a `sequence.pwsseq` file containing the sequence information.
        paths = [i.filePath for i in cells]
        commonPath = os.path.commonpath(paths)
        # We will search up to 3 parent directories for a sequence file
        for i in range(3):
            if os.path.exists(os.path.join(commonPath, 'sequence.pwsseq')):
                with open(os.path.join(commonPath, 'sequence.pwsseq')) as f:
                    self._sequence = SequencerStep.fromJson(f.read())
                    self._cells = [i for i in cells if i.sequencerCoordinate is not None]  # TODO should probably verify that the coords match up with the sequence we loaded.
                    self._ui.setSequenceStepRoot(self._sequence)
                return
            commonPath = os.path.split(commonPath)[0]  # Go up one directory
        # We only get this far if the sequence search fails.
        self._sequence = None
        self._cells = None

    def getName(self) -> str:
        """The name to refer to this plugin by."""
        return "Acquisition Sequence Selector"

    def onPluginSelected(self):
        """This method will be called when the plugin is activated."""
        self._ui.show()  # We use ui visibility to determine if the plugin is active or not.
        self.onNewCellsLoaded(self._selector.getAllCellMetas())  # Make sure we're all up to date

    def _updateSelectorSelection(self, steps: typing.List[SequencerStep]):
        


class SequenceViewer(QWidget):
    stepSelectionChanged = pyqtSignal(list)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        l = QHBoxLayout()
        self.setLayout(l)

        self._sequenceTree = QTreeWidget()
        self._sequenceTree.setColumnCount(2)
        self._sequenceTree.setIndentation(10)

        self._settingsTree = DictTreeView()
        self._settingsTree.setColumnCount(2)
        self._settingsTree.setIndentation(10)
        self._sequenceTree.itemClicked.connect(lambda item, column: self._settingsTree.setDict(item.settings))

        self._sequenceTree.itemSelectionChanged.connect(lambda: self.stepSelectionChanged.emit(self._sequenceTree.selectedItems()))

        l.addWidget(self._sequenceTree)
        l.addWidget(self._settingsTree)

    def setSequenceStepRoot(self, root: SequencerStep):
        self._sequenceTree.clear()
        self._sequenceTree.addTopLevelItem(root)
        root.setExpanded(True)
