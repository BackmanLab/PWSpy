import typing

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QItemSelection, QModelIndex, QItemSelectionModel
from PyQt5.QtWidgets import QTreeView, QWidget, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QAbstractItemDelegate

from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer._treeModel.model import TreeModel
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.steps import SequencerStep
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer._ui.Delegate import IterationRangeDelegate
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.sequencerCoordinate import IterationRangeCoordStep, \
    SequencerCoordinateRange


class MyTreeView(QTreeView):
    newCoordSelected = pyqtSignal(SequencerCoordinateRange)
    currentItemChanged = pyqtSignal(SequencerStep)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        delegate = IterationRangeDelegate(self)
        self.setItemDelegate(delegate)
        delegate.editingFinished.connect(lambda: self._selectionChanged(self.selectionModel().selection())) # When we edit an item we still want to process it as a change even though the selection hasn't changed.
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)  # Make editing start on a single click.
        self.setIndentation(10)  # Reduce the default indentation
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)  # Smooth scrolling
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self._currentCoordRange = None

    def commitAndClose(self):
        #Quickly deselect and reselect. this forces any open editor to commit its changes.
        idx = self.currentIndex()
        self.setCurrentIndex(QModelIndex())
        self.setCurrentIndex(idx)

        delegate: IterationRangeDelegate = self.itemDelegate()
        self.closeEditor(delegate.editor, QAbstractItemDelegate.NoHint)  # Close the editor to indicate to the user that the change has been accepted.

    def setRoot(self, root: SequencerStep) -> None:
        """
        Populate the widget with a sequence of acquisition steps

        Args:
            root: The Root step of the acquisition sequence. All other steps are children of this step.
        """
        self.setModel(TreeModel(root))
        self.setSelectionModel(QItemSelectionModel(self.model(), self))
        self.selectionModel().selectionChanged.connect(self._selectionChanged)
        self.selectionModel().currentChanged.connect(self._currentChanged)

    def _selectionChanged(self, selected: QItemSelection, deselected: QItemSelection = None):
        try:
            idx = selected.indexes()[0]  # We only support a single selection anyways.
        except IndexError:
            return  # Sometime this can get fired with no selected indexes.
        step: SequencerStep = idx.internalPointer()
        coordSteps = []
        while step is not self.model().invisibleRootItem(): # This will break out once we reach the root item.
            coordStep = step.data(QtCore.Qt.EditRole)  # The item delegate saves an iterationRangeCoordStep in the `editRole` data slot of steps.
            if coordStep is None:
                coordSteps.append(IterationRangeCoordStep(step.id, None))
            else:
                coordSteps.append(coordStep)
            step = step.parent()  # On the next iteration look at the parent of the selected step.
        self._currentCoordRange = SequencerCoordinateRange(list(reversed(coordSteps)))
        self.newCoordSelected.emit(self._currentCoordRange)

    def getCurrentSelectedCoordinateRange(self):
        return self._currentCoordRange

    def _currentChanged(self, current: QModelIndex, previous: QModelIndex):
        if current.internalPointer() is not None: # In some cases we may change to index to something blank that has not pointer
            self.currentItemChanged.emit(current.internalPointer())


class DictTreeView(QTreeWidget):
    """
    A QTreeWidget that displays that contents of a Python `dict`
    Read-Only.
    """

    def setDict(self, d: dict) -> None:
        """
        Set the `dict` that this widget displays.

        Args:
            d: The dictionary to display the contents of.
        """
        self.clear()
        self._fillItem(self.invisibleRootItem(), d)

    @staticmethod
    def _fillItem(item: QTreeWidgetItem, value: typing.Union[dict, list]):
        """Recursively populate a tree item with children to match the contents of a `dict`"""
        item.setExpanded(True)
        if isinstance(value, dict):
            for key, val in value.items():
                child = QTreeWidgetItem()
                child.setText(0, f"{key}")
                item.addChild(child)
                if isinstance(val, (list, dict)):
                    DictTreeView._fillItem(child, val)
                else:
                    child.setText(1, f"{val}")
        elif isinstance(value, list):
            for val in value:
                child = QTreeWidgetItem()
                item.addChild(child)
                if type(val) is dict:
                    child.setText(0, '[dict]')
                    DictTreeView._fillItem(child, val)
                elif type(val) is list:
                    child.setText(0, '[list]')
                    DictTreeView._fillItem(child, val)
                else:
                    child.setText(0, val)
                    child.setExpanded(True)


