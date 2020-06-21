from __future__ import annotations
import abc
from typing import List

from pwspy import dataTypes as pwsdt
from pwspy.apps.PWSAnalysisApp.componentInterfaces import QABCMeta, CellSelector


class CellSelectorPluginSupport:
    """A utility class to help manage CellSelectorPlugins"""
    def __init__(self, selector: CellSelector):
        self._plugins: List[CellSelectorPlugin] = []
        self._selector = selector

    def registerPlugin(self, plugin: CellSelectorPlugin):
        self._plugins.append(plugin)
        plugin.setContext(self._selector)

    def getPlugins(self):
        return self._plugins

    def notifyCellSelectionChanged(self, cells: List[pwsdt.AcqDir]):
        for plugin in self._plugins:
            plugin.onCellsSelected(cells)

    def notifyReferenceSelectionChanged(self, cell: pwsdt.AcqDir):
        for plugin in self._plugins:
            plugin.onReferenceSelected(cell)

    def notifyNewCellsLoaded(self, cells: List[pwsdt.AcqDir]):
        for plugin in self._plugins:
            plugin.onNewCellsLoaded(cells)


class CellSelectorPlugin(metaclass=QABCMeta):
    @abc.abstractmethod
    def setContext(self, selector: CellSelector):
        """Set the CellSelector that this plugin is associated to. This should happen before anything else."""
        pass

    @abc.abstractmethod
    def onCellsSelected(self, cells: List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that it has had new cells selected."""
        pass

    @abc.abstractmethod
    def onReferenceSelected(self, cell: pwsdt.AcqDir):
        """This method will be called when the CellSelector indicates that it has had a new reference selected."""
        pass

    @abc.abstractmethod
    def onNewCellsLoaded(self, cells: List[pwsdt.AcqDir]):
        """This method will be called when the CellSelector indicates that new cells have been loaded to the selector."""
        pass

    @abc.abstractmethod
    def getName(self) -> str:
        """The name to refer to this plugin by."""
        pass

    @abc.abstractmethod
    def onPluginSelected(self):
        """This method will be called when the plugin is activated."""
        pass