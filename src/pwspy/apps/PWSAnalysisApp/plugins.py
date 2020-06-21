import abc
from typing import List

from pwspy import dataTypes as pwsdt
from pwspy.apps.PWSAnalysisApp.componentInterfaces import QABCMeta, CellSelector


class CellSelectorPlugin(metaclass=QABCMeta):
    @abc.abstractmethod
    def setContext(self, selector: CellSelector): pass

    @abc.abstractmethod
    def onCellsSelected(self, cells: List[pwsdt.AcqDir]): pass

    @abc.abstractmethod
    def onNewCellsLoaded(self, cells: List[pwsdt.AcqDir]): pass