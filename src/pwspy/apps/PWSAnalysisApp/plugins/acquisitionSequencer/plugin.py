import typing

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QApplication

from pwspy.apps.PWSAnalysisApp.componentInterfaces import CellSelector
from pwspy.apps.PWSAnalysisApp.pluginInterfaces import CellSelectorPlugin
import pwspy.dataTypes as pwsdt
import os

from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.TreeView import DictTreeView, MyTreeView
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.sequencerCoordinate import SequencerCoordinateRange, \
    SeqAcqDir
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.steps import SequencerStep
from pwspy.dataTypes import AcqDir


def requirePluginActive(method):
    def newMethod(self, *args, **kwargs):
        if self._ui.isVisible():  # If the ui isn't visible then we consider the plugin to be off.
            method(self, *args, **kwargs)
    return newMethod


class AcquisitionSequencerPlugin(CellSelectorPlugin):
    def __init__(self):
        self._selector: CellSelector = None
        self._sequence: SequencerStep = None
        self._cells: typing.List[SeqAcqDir] = None
        self._ui = SequenceViewer()
        self._ui.newCoordSelected.connect(self._updateSelectorSelection)

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
        if len(cells) == 0: # This causes a crash
            return
        #Search the parent directory for a `sequence.pwsseq` file containing the sequence information.
        paths = [i.filePath for i in cells]
        commonPath = os.path.commonpath(paths)
        # We will search up to 3 parent directories for a sequence file
        for i in range(3):
            if os.path.exists(os.path.join(commonPath, 'sequence.pwsseq')):
                with open(os.path.join(commonPath, 'sequence.pwsseq')) as f:
                    self._sequence = SequencerStep.fromJson(f.read())
                    self._cells = []
                    for i in cells:
                        try:
                            self._cells.append(SeqAcqDir(i)) # TODO should probably verify that the coords match up with the sequence we loaded.
                        except:  # Coordinates weren't found
                            pass
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

    def _updateSelectorSelection(self, coordRange: SequencerCoordinateRange):
        select: typing.List[AcqDir] = []
        for cell in self._cells:
            if cell.sequencerCoordinate in coordRange:
                select.append(cell.acquisitionDirectory)
        self._selector.setSelectedCells(select)


class SequenceViewer(QWidget):
    newCoordSelected = pyqtSignal(SequencerCoordinateRange)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Acquisition Sequence Viewer")

        l = QHBoxLayout()
        self.setLayout(l)

        self._sequenceTree = MyTreeView(self)

        self._settingsTree = DictTreeView()
        self._settingsTree.setColumnCount(2)
        self._settingsTree.setIndentation(10)
        self._sequenceTree.currentItemChanged.connect(lambda item: self._settingsTree.setDict(item.settings))

        self._sequenceTree.newCoordSelected.connect(lambda coordRange: self.newCoordSelected.emit(coordRange))

        l.addWidget(self._sequenceTree)
        l.addWidget(self._settingsTree)

    def setSequenceStepRoot(self, root: SequencerStep):
        self._sequenceTree.setRoot(root)
        self._sequenceTree.expandAll()


if __name__ == '__main__':
    with open(r'C:\Users\nicke\Desktop\data\toast2\sequence.pwsseq') as f:
        s = SequencerStep.fromJson(f.read())
    import sys
    from pwspy import dataTypes as pwsdt
    from glob import glob

    acqs = [pwsdt.AcqDir(i) for i in glob(r"C:\Users\nicke\Desktop\data\toast2\Cell*")]
    sacqs = [SeqAcqDir(acq) for acq in acqs]

    import sys

    app = QApplication(sys.argv)


    view = MyTreeView()
    view.setRoot(s)

    view.setWindowTitle("Simple Tree Model")
    view.show()
    sys.exit(app.exec_())


    app = QApplication(sys.argv)

    W = QWidget()
    W.setLayout(QHBoxLayout())

    w = QTreeWidget()
    w.setColumnCount(2)
    w.addTopLevelItem(s)
    w.setIndentation(10)

    w2 = DictTreeView()
    w2.setColumnCount(2)
    w2.setIndentation(10)


    w.itemClicked.connect(lambda item, column: w2.setDict(item.settings))

    W.layout().addWidget(w)
    W.layout().addWidget(w2)


    W.show()
    app.exec()
    a = 1
