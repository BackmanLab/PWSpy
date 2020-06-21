import typing

from pwspy.apps.PWSAnalysisApp.componentInterfaces import CellSelector
from pwspy.apps.PWSAnalysisApp.pluginInterfaces import CellSelectorPlugin
import pwspy.dataTypes as pwsdt
import os

class AcquisitionSequencerPlugin(CellSelectorPlugin):
    def __init__(self):
        self._selector = None
        self._sequence = None
        self._cells: typing.List[pwsdt.AcqDir] = None

    def setContext(self, selector: CellSelector):
        """set the CellSelector that this plugin is associated to."""
        self._selector = selector

    def onCellsSelected(self, cells: typing.List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that it has had new cells selected."""
        pass

    def onReferenceSelected(self, cell: pwsdt.AcqDir):
        """This method will be called when the CellSelector indicates that it has had a new reference selected."""
        pass

    def onNewCellsLoaded(self, cells: typing.List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that new cells have been loaded to the selector."""
        #Search the parent directory for a `sequence.pwsseq` file containing the sequence information.
        paths = [i.filePath for i in cells]
        commonPath = os.path.commonpath(paths)
        # We will search up to 3 parent directories for a sequence file
        for i in range(3):
            if os.path.exists(os.path.join(commonPath, 'seqeunce.pwsseq')):
                break
            commonPath = os.path.split(commonPath)[0]  # Go up one directory

        #Search the loaded cells for sequence coordinates, save the cells that have some
        self._cells = [i for i in cells if i.sequencerCoordinate is not None]
        #TODO should probably verify that the coords match up with the sequence we loaded.

    def getName(self) -> str:
        """The name to refer to this plugin by."""
        return "Acquisition Sequence Selector"

    def onPluginSelected(self):
        """This method will be called when the plugin is activated."""
        pass