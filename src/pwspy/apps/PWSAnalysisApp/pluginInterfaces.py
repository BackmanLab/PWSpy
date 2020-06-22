from __future__ import annotations
import abc
from typing import List

from pwspy import dataTypes as pwsdt
from pwspy.apps.PWSAnalysisApp.componentInterfaces import QABCMeta, CellSelector
import pwspy.apps.PWSAnalysisApp.plugins

class CellSelectorPluginSupport:
    """A utility class to help manage CellSelectorPlugins"""
    def __init__(self, selector: CellSelector):
        pluginClasses = self._findPlugins()
        self._plugins: List[CellSelectorPlugin] = [clazz() for clazz in pluginClasses]
        for p in self._plugins:
            p.setContext(selector)
        self._selector = selector

    def _findPlugins(self):
        """Scans the contents of pwspy.appsPWSAnalysisApp.plugins for any modules containing subclasses of CellSelectorPlugin.
        If someone wants to add a plugin without modifying this source code they can use namespace packages to make
        it seem as though their plugin module is in pwspy.appsPWSAnalysisApp.plugins"""
        import pkgutil, importlib, inspect
        iter_namespace = lambda pkg: pkgutil.iter_modules(pkg.__path__, pkg.__name__ + ".")  # Based on something I saw here https://packaging.python.org/guides/creating-and-discovering-plugins/#using-namespace-packages
        plugins = []

        for finder, name, ispkg in iter_namespace(pwspy.apps.PWSAnalysisApp.plugins):  # Find all submodules of the root module
            mod = importlib.import_module(name)
            clsmembers = inspect.getmembers(mod, lambda member: inspect.isclass(member) and member.__module__ == name)  # Get all the classes that are defined in the module
            for name, cls in clsmembers:
                if issubclass(cls, CellSelectorPlugin):
                    plugins.append(cls)  # Add any class that implements the plugin base class
        return plugins

    # def registerPlugin(self, plugin: CellSelectorPlugin):  # this is from before we automatically scanned for plugins.
    #     self._plugins.append(plugin)
    #     plugin.setContext(self._selector)

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
    """Implementions of this class should require no args for the constructor"""
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

if __name__ == '__main__':
    s = CellSelectorPluginSupport(None)
    d = s._findPlugins()
    a = 1
