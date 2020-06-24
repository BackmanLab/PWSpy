import typing

from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import pyqtSignal, QItemSelection
from PyQt5.QtWidgets import QTreeView, QWidget, QTreeWidget, QTreeWidgetItem, QAbstractItemView

from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer import SequencerStep
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.Delegate import IterationRangeDelegate
from pwspy.apps.PWSAnalysisApp.plugins.acquisitionSequencer.sequencerCoordinate import IterationRangeCoordStep, \
    SequencerCoordinateRange


class MyTreeView(QTreeView):
    newCoordSelected = pyqtSignal(SequencerCoordinateRange)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent=parent)
        self.setItemDelegate(IterationRangeDelegate(self))
        self.setEditTriggers(QAbstractItemView.AllEditTriggers)  # Make editing start on a single click.
        self.setIndentation(10)  # Reduce the default indentation
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)  # Smooth scrolling

        self.selectionModel().selectionChanged.connect(self._selectionChanged)

    def _selectionChanged(self, selected: QItemSelection, deselected: QItemSelection):
        step: SequencerStep = selected.first()  # We only support a single selection anyways.
        coordSteps = []
        while step is not None: # This will break out once we reach the root item.
            coordStep = step.data(QtCore.Qt.EditRole)  # The item delegate saves an iterationRangeCoordStep in the edit role of steps.
            if coordStep is None:
                coordSteps.append(IterationRangeCoordStep(step.id, None))
            else:
                coordSteps.append(coordStep)
        self.newCoordSelected.emit(SequencerCoordinateRange(list(reversed(coordSteps))))


class DictTreeView(QTreeWidget):
    def setDict(self, d: dict):
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


