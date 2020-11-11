from __future__ import annotations
import typing

from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QApplication

from pwspy.apps.PWSAnalysisApp.pluginInterfaces import CellSelectorPlugin
import os

from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer._ui.TreeView import MyTreeView
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer._ui.widget import SequenceViewer
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.sequencerCoordinate import SequencerCoordinateRange, SeqAcqDir
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.steps import SequencerStep
from pwspy.dataTypes import AcqDir
if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp.componentInterfaces import CellSelector


def requirePluginActive(method):
    def newMethod(self, *args, **kwargs):
        if self._ui.isVisible():  # If the ui isn't visible then we consider the plugin to be off.
            method(self, *args, **kwargs)
    return newMethod


class AcquisitionSequencerPlugin(CellSelectorPlugin): #TODO switch to a qdialog or dock widget, make sure widget has a parent. Provide new columns to the cell selector and results selector with coordinate?
    def __init__(self):
        self._selector: CellSelector = None
        self._sequence: SequencerStep = None
        self._cells: typing.List[SeqAcqDir] = None
        self._ui = SequenceViewer()
        self._ui.newCoordSelected.connect(self._updateSelectorSelection)

    def setContext(self, selector: CellSelector, parent: QWidget):
        """set the CellSelector that this plugin is associated to."""
        self._selector = selector
        self._ui.setParent(parent)
        self._ui.setWindowFlags(QtCore.Qt.Window) # Without this is just gets added to the main window in a weird way.

    @requirePluginActive
    def onCellsSelected(self, cells: typing.List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that it has had new cells selected."""
        pass

    @requirePluginActive
    def onReferenceSelected(self, cell: pwsdt.AcqDir):
        """This method will be called when the CellSelector indicates that it has had a new reference selected."""
        pass

    def onNewCellsLoaded(self, cells: typing.List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that new cells have been loaded to the selector."""
        if len(cells) == 0:  # This causes a crash
            return
        #Search the parent directory for a `sequence.pwsseq` file containing the sequence information.
        paths = [i.filePath for i in cells]
        commonPath = os.path.commonpath(paths)
        # We will search up to 3 parent directories for a sequence file
        for i in range(3):
            if os.path.exists(os.path.join(commonPath, 'sequence.pwsseq')):
                with open(os.path.join(commonPath, 'sequence.pwsseq')) as f:
                    try:
                        self._sequence = SequencerStep.fromJson(f.read())
                    except:  # if the file format is messed up this will fail, dont' let it crash the whole plugin though.
                        commonPath = os.path.split(commonPath)[0]  # Go up one directory
                        continue
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

    def additionalColumnNames(self) -> typing.Sequence[str]:
        """The header names for each column."""
        return tuple() #return "Coord. Type", "Coord. Value" # We used to add new columns, but it was confusing, better not to.

    def getTableWidgets(self, acq: pwsdt.AcqDir) -> typing.Sequence[QWidget]:  #TODO this gets called before the sequence has been loaded. Make it so this isn't required for constructor of cell table widgets.
        """provide a widget for each additional column to represent `acq`"""
        return tuple()
        # typeNames = {SequencerStepTypes.POS.name: "Position", SequencerStepTypes.TIME.name: "Time", SequencerStepTypes.ZSTACK.name: "Z Stack"}
        # try:
        #     acq = SeqAcqDir(acq)
        # except:
        #     return tuple((QTableWidgetItem(), QTableWidgetItem()))
        # coord = acq.sequencerCoordinate
        # idx, iteration = [(i, iteration) for i, iteration in enumerate(coord.iterations) if iteration is not None][-1]
        # for step in self._sequence.iterateChildren():
        #     if step.id == coord.ids[idx]:
        #         step: CoordSequencerStep
        #         val = QTableWidgetItem(step.getIterationName(iteration))
        #         t = QTableWidgetItem(typeNames[step.stepType])
        #         return tuple((t, val))
        # return tuple((QTableWidgetItem(), QTableWidgetItem()))  # This will happen if the acquisition has a coords file but the coord isn't actually found in the sequence file.
        #

    def _updateSelectorSelection(self, coordRange: SequencerCoordinateRange):
        select: typing.List[AcqDir] = []
        for cell in self._cells:
            if cell.sequencerCoordinate in coordRange:
                select.append(cell)
        self._selector.setSelectedCells(select)


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
