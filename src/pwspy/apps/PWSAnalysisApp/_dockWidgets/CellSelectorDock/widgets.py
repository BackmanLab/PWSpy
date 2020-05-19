# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

import json
import logging
import os
import typing
from json import JSONDecodeError
from typing import List, Optional, Type

from IPython.core.magics import logging
from PyQt5 import QtCore, QtGui
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QPushButton, QTableWidgetItem, QTableWidget, QAbstractItemView, QMenu, QWidget, QMessageBox, \
    QInputDialog, QHeaderView

from pwspy.apps.PWSAnalysisApp._sharedWidgets import ScrollableMessageBox
from pwspy.dataTypes import AcqDir, ICMetaData, DynMetaData

from pwspy.apps.PWSAnalysisApp._sharedWidgets.dictDisplayTree import DictDisplayTreeDialog
from pwspy.apps.PWSAnalysisApp._sharedWidgets.tables import NumberTableWidgetItem

def evalToolTip(cls: Type[QWidget], method):
    """Given a QWidget and a function that returns a string, this decorator returns a modified class that will evaluate
    the function each time the tooltip is requested."""
    class newClass(cls):
        def event(self, e: QtCore.QEvent):
            if e.type() == QtCore.QEvent.ToolTip:
                self.setToolTip(method())
            return super().event(e)
    return newClass


class CellTableWidgetItem:
    """Represents a single row of the CellTableWidget and corresponds to a single PWS acquisition."""
    def __init__(self, acq: AcqDir, label: str, num: int):
        self.acqDir = acq
        self.num = num
        self.path = label
        self.notesButton = evalToolTip(QPushButton, acq.getNotes)("Open")
        self.notesButton.setFixedSize(40, 30)
        self.pathLabel = QTableWidgetItem(self.path)
        self.numLabel = NumberTableWidgetItem(num)
        self.roiLabel = NumberTableWidgetItem(0)
        self.anLabel = NumberTableWidgetItem(0)
        self.notesButton.released.connect(self.acqDir.editNotes)
        self.pLabel = QTableWidgetItem()
        self.pLabel.setToolTip("Indicates if PWS measurement is present")
        self.dLabel = QTableWidgetItem()
        self.dLabel.setToolTip("Indicates if Dynamics measurement is present")
        self.fLabel = QTableWidgetItem()
        self.fLabel.setToolTip("Indicates if Fluorescence measurement is present")
        for i in [self.pLabel, self.dLabel, self.fLabel]:
            i.setTextAlignment(QtCore.Qt.AlignCenter)
        if self.acqDir.pws is not None: self.pLabel.setText('Y'); self.pLabel.setBackground(QtCore.Qt.darkGreen)
        else: self.pLabel.setText('N'); self.pLabel.setBackground(QtCore.Qt.white)
        if self.acqDir.dynamics is not None: self.dLabel.setText('Y'); self.dLabel.setBackground(QtCore.Qt.darkGreen)
        else: self.dLabel.setText('N'); self.dLabel.setBackground(QtCore.Qt.white)
        if self.acqDir.fluorescence is not None: self.fLabel.setText('Y'); self.fLabel.setBackground(QtCore.Qt.darkGreen)
        else: self.fLabel.setText('N'); self.fLabel.setBackground(QtCore.Qt.white)
        self._items = [self.pathLabel, self.numLabel, self.roiLabel, self.anLabel] #This list is used for changing background color and for setting all items selected.
        self.refresh()
        self.mdPath = os.path.join(self.acqDir.filePath, 'AnAppPrefs.json')
        try:
            with open(self.mdPath, 'r') as f:
                self.md = json.load(f)
        except (JSONDecodeError, FileNotFoundError):
            self.md = {'invalid': False, 'reference': False}
        self.setInvalid(self._invalid, save=False) #Update item color based on saved status. Since invalid status overrides reference status we must do this first.
        self.setReference(self._reference, save=False) #We override the default automatic saving of metadata since we're just loading anyway, nothing has been changed.

    @property
    def row(self):
        """Since this can be added to a table that uses sorting we can't know that the row number will remain constant.
        This should return the correct row number."""
        return self.numLabel.row()

    def setInvalid(self, invalid: bool, save: bool = True):
        if invalid:
            self._setItemColor(QtCore.Qt.red)
            self._reference = False
        else:
            self._setItemColor(QtCore.Qt.white)
        self._invalid = invalid
        if save: self._saveMetadata()

    def setReference(self, reference: bool, save: bool = True) -> None:
        if self.isInvalid():
            return
        if reference:
            self._setItemColor(QtCore.Qt.darkGreen)
        else:
            self._setItemColor(QtCore.Qt.white)
        self._reference = reference
        if save: self._saveMetadata()

    def isInvalid(self) -> bool:
        return self._invalid

    def isReference(self) -> bool:
        return self._reference

    def setSelected(self, select: bool):
        for i in self._items:
            i.setSelected(select)

    def setHighlighted(self, select: bool):
        originalFont = self._items[0].font()
        originalFont.setBold(select)
        for i in self._items:
            i.setFont(originalFont)

    def close(self):
        self._saveMetadata()

    def refresh(self):
        """Set the number of roi's and analyses. Update the tooltips."""
        rois = self.acqDir.getRois()
        self.roiLabel.setNumber(len(rois))
        anNumber = 0 #This is in case the next few statements evaluate to false.
        anToolTip = ""
        if self.acqDir.pws is not None:
            pwsAnalyses = self.acqDir.pws.getAnalyses()
            anNumber += len(pwsAnalyses)
            if len(pwsAnalyses) != 0:
                anToolTip += "PWS:" + ', '.join(pwsAnalyses)
        if self.acqDir.dynamics is not None:
            dynAnalyses = self.acqDir.dynamics.getAnalyses()
            anNumber += len(dynAnalyses)
            if len(dynAnalyses) != 0:
                anToolTip += "\nDYN:" + ', '.join(dynAnalyses)
        self.anLabel.setNumber(anNumber)
        self.anLabel.setToolTip(anToolTip)
        if self.acqDir.getNotes() != '':
            self.notesButton.setStyleSheet('QPushButton { background-color: lightgreen;}')
        else:
            self.notesButton.setStyleSheet('QPushButton { background-color: lightgrey;}')

        nameNums = [(name, num) for name, num, fformat in rois]
        if len(nameNums) > 0:
            names = set(list(zip(*nameNums))[0])
            d = {name: [num for nname, num in nameNums if nname == name] for name in names}
            self.roiLabel.setToolTip("\n".join([f'{k}: {v}' for k, v in d.items()]))


    @property
    def _invalid(self): return self.md['invalid']

    @_invalid.setter
    def _invalid(self, val): self.md['invalid'] = val

    @property
    def _reference(self): return self.md['reference']

    @_reference.setter
    def _reference(self, val): self.md['reference'] = val

    def _saveMetadata(self):
        try:
            with open(self.mdPath, 'w') as f:
                json.dump(self.md, f)
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.warning("Failed to save app metadata for self.mdPath")

    def __del__(self):
        self.close() #This is here just in case. realistacally del rarely gets called, need to manually close each cell item.

    def _setItemColor(self, color):
        for i in self._items:
            i.setBackground(color)

class CellTableWidget(QTableWidget):
    """This is the table from which the user can select which cells to analyze, plot, etc. Each row of the table is
    represented by a CellTableWidgetItem which are stored in the self._cellItems list"""
    referencesChanged = QtCore.pyqtSignal(bool, list)
    itemsCleared = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setSortingEnabled(True)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        columns = ('Path', 'Cell#', 'ROIs', 'Analyses', 'Notes', 'P', 'D', 'F')
        self.setRowCount(0)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self.verticalHeader().hide()
        [self.setColumnWidth(i, w) for i, w in zip(range(len(columns)), [60, 40, 40, 50, 40, 20, 20, 20])] #Set the column widths
        [self.horizontalHeader().setSectionResizeMode(i, self.horizontalHeader().Fixed) for i in [4, 5, 6, 7]] #set the notes, and p/d/f columns nonresizeable
        self._cellItems = []
        #This makes the items stay looking selected even when the table is inactive
        self.setStyleSheet("""QTableWidget::item:active {
                                selection-background-color: darkblue;
                                selection-color: white;}
                                
                                QTableWidget::item:inactive {
                                selection-background-color: darkblue;
                                selection-color: white;}""")
        self.palette().setColor(QPalette.Highlight, QtGui.QColor("#3a7fc2")) # This makes it so the selected cells stay colored even when the table isn't active.
        self.palette().setColor(QPalette.HighlightedText, QtCore.Qt.white)

    @property
    def cellItems(self) -> List[CellTableWidgetItem]:
        return self._cellItems

    @property
    def selectedCellItems(self) -> typing.List[CellTableWidgetItem]:
        """Returns the rows that have been selected."""
        rowIndices = [i.row() for i in self.selectedIndexes()[::self.columnCount()]]
        rowIndices.sort()
        _ = {i.row: i for i in self._cellItems} #Cell items keyed by their current row position.
        return [_[i] for i in rowIndices]

    def refreshCellItems(self):
        for i in self._cellItems:
            i.refresh()

    def addCellItem(self, item: CellTableWidgetItem) -> None:
        row = len(self._cellItems)
        self.setSortingEnabled(False)  # The fact that we are adding items assuming its the last row is a problem if sorting is on.
        self.setRowCount(row + 1)
        self.setItem(row, 0, item.pathLabel)
        self.setItem(row, 1, item.numLabel)
        self.setItem(row, 2, item.roiLabel)
        self.setItem(row, 3, item.anLabel)
        self.setCellWidget(row, 4, item.notesButton)
        self.setItem(row, 5, item.pLabel)
        self.setItem(row, 6, item.dLabel)
        self.setItem(row, 7, item.fLabel)
        self.setSortingEnabled(True)
        self._cellItems.append(item)

    def addCellItems(self, items: List[CellTableWidgetItem]) -> None:
        row = len(self._cellItems)
        self.setSortingEnabled(False)
        self.setRowCount(row + len(items))
        for i, item in enumerate(items):
            newrow = row + i
            self.setItem(newrow, 0, item.pathLabel)
            self.setItem(newrow, 1, item.numLabel)
            self.setItem(newrow, 2, item.roiLabel)
            self.setItem(newrow, 3, item.anLabel)
            self.setCellWidget(newrow, 4, item.notesButton)
            self.setItem(newrow, 5, item.pLabel)
            self.setItem(newrow, 6, item.dLabel)
            self.setItem(newrow, 7, item.fLabel)
        self.setSortingEnabled(True)
        self._cellItems.extend(items)

    def clearCellItems(self) -> None:
        self.setRowCount(0)
        for c in self._cellItems:
            c.close() #This causes the cell item to save it's metadata.
        self._cellItems = []
        self.itemsCleared.emit()

    def _showContextMenu(self, point: QtCore.QPoint):
        if len(self.selectedCellItems) > 0:
            menu = QMenu("Context Menu")
            state = not self.selectedCellItems[0].isInvalid()
            stateString = "Disable Cell(s)" if state else "Enable Cell(s)"
            refState = not self.selectedCellItems[0].isReference()
            refStateString = "Set as Reference" if refState else "Unset as Reference"
            invalidAction = menu.addAction(stateString)
            invalidAction.triggered.connect(lambda: self._toggleSelectedCellsInvalid(state))
            refAction = menu.addAction(refStateString)
            refAction.triggered.connect(lambda: self._toggleSelectedCellsReference(refState))

            menu.addSeparator()
            mdAction = menu.addAction("Display Metadata")
            mdAction.triggered.connect(self._displayCellMetadata)
            anAction = menu.addAction("View analysis settings")
            anAction.triggered.connect(self._displayAnalysisSettings)

            menu.addSeparator()
            delAnAction = menu.addAction("Delete analysis by name")
            delAnAction.triggered.connect(self._deleteAnalysisByName)
            delRoiAction = menu.addAction("Delete ROIs by name")
            delRoiAction.triggered.connect(self._deleteRoisByName)

            menu.exec(self.mapToGlobal(point))

    def _deleteAnalysisByName(self):
        anName, clickedOk = QInputDialog.getText(self, "Analysis Name", "Analysis name to delete")
        if not clickedOk:
            return
        deletableCells = []
        for i in self.selectedCellItems:
            if i.acqDir.pws is not None:
                if anName in i.acqDir.pws.getAnalyses():
                    deletableCells.append(i.acqDir.pws)
            if i.acqDir.dynamics is not None:
                if anName in i.acqDir.dynamics.getAnalyses():
                    deletableCells.append(i.acqDir.dynamics)
        if len(deletableCells)==0:
            QMessageBox.information(self, "Hmm", "No matching analysis files were found.")
        else:
            ret = ScrollableMessageBox.question(self, "Delete Analysis?",
                f"Are you sure you want to delete {anName} from:"
                f"\nPWS: {', '.join([os.path.split(i.acquisitionDirectory.filePath)[-1] for i in deletableCells if isinstance(i, ICMetaData)])}"
                f"\nDynamics: {', '.join([os.path.split(i.acquisitionDirectory.filePath)[-1] for i in deletableCells if isinstance(i, DynMetaData)])}")
            if ret == QMessageBox.Yes:
                [i.removeAnalysis(anName) for i in deletableCells]
            self.refreshCellItems()

    def _deleteRoisByName(self):
        roiName, clickeOk = QInputDialog.getText(self, "ROI Name", "ROI name to delete")
        if not clickeOk:
            return
        deletableCells = []
        for i in self.selectedCellItems:
            if roiName in [roiName for roiName, roiNum, fformat in i.acqDir.getRois()]:
                deletableCells.append(i.acqDir)
        if len(deletableCells)==0:
            QMessageBox.information(self, "Hmm", "No matching ROI files were found.")
        else:
            if ScrollableMessageBox.question(self, "Delete ROI?",
                                             f"Are you sure you want to delete ROI: {roiName} from: \n{', '.join([os.path.split(i.filePath)[-1] for i in deletableCells])}") == QMessageBox.Yes:
                [i.deleteRoi(roiName, roiNum) for i in deletableCells for ROIName, roiNum, fformat in i.getRois() if ROIName == roiName]
            self.refreshCellItems()

    def _displayAnalysisSettings(self):
        analyses = set()
        for i in self.selectedCellItems:
            #We assume that analyses with the same name have the same settings
            analyses.update(i.acqDir.pws.getAnalyses())
        for an in analyses:
            for i in self.selectedCellItems:
                if an in i.acqDir.pws.getAnalyses():
                    d = DictDisplayTreeDialog(self, i.acqDir.pws.loadAnalysis(an).settings._asDict(), title=an)
                    d.show()
                    break

    def _displayCellMetadata(self):
        for i in self.selectedCellItems:
            d = DictDisplayTreeDialog(self, i.acqDir.pws._dict, title=os.path.join(i.path, f"Cell{i.num}"))
            d.show()

    def _toggleSelectedCellsInvalid(self, state: bool):
        changedItems = []
        for i in self.selectedCellItems:
            if i.isInvalid() != state:
                i.setInvalid(state)
                changedItems.append(i)
        if state:
            self.referencesChanged.emit(False, changedItems)

    def _toggleSelectedCellsReference(self, state: bool) -> None:
        """State indicates whether the cells are being marked as reference or as non-reference."""
        items = self.selectedCellItems
        changedItems = []
        for i in items:
            if (i.isReference() != state) and (not i.isInvalid()):
                i.setReference(state)
                changedItems.append(i)
        self.referencesChanged.emit(state, changedItems)


class ReferencesTableItem(QTableWidgetItem):
    """A single row of the reference table."""
    def __init__(self, item: CellTableWidgetItem):
        self.item = item
        super().__init__(os.path.join(item.pathLabel.text(), f'Cell{item.num}'))
        self.setToolTip(os.path.join(item.pathLabel.text(), f'Cell{item.num}'))

    def setHighlighted(self, select: bool):
        originalFont = self.font()
        originalFont.setBold(select)
        self.setFont(originalFont)


class ReferencesTable(QTableWidget):
    """This table shows all acquisitions which can be used as a reference in an analysis."""
    def __init__(self, parent: QWidget, cellTable: CellTableWidget):
        super().__init__(parent)
        #This makes the items stay looking selected even when the table is inactive
        self.setStyleSheet("""QTableWidget::item:active {   
                                selection-background-color: darkblue;
                                selection-color: white;}
                                QTableWidget::item:inactive {
                                selection-background-color: darkblue;
                                selection-color: white;}""")
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setColumnCount(1)
        self.setHorizontalHeaderLabels(('Reference',))
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setRowCount(0)
        self.verticalHeader().hide()
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)
        cellTable.referencesChanged.connect(self.updateReferences)
        cellTable.itemsCleared.connect(self._clearItems)
        self._references: typing.List[CellTableWidgetItem] = []

    def updateReferences(self, state: bool, items: typing.List[CellTableWidgetItem]):
        """state indicates if the cells are being added or being removed as references."""
        if state:
            for item in items:
                if item not in self._references:
                    row = len(self._references)
                    self.setRowCount(row + 1)
                    self.setItem(row, 0, ReferencesTableItem(item))
                    self._references.append(item)
        else:
            for item in items:
                if item in self._references:
                    self._references.remove(item)
                    item.setReference(False)
                    # find row number
                    for i in range(self.rowCount()):
                        if item is self.item(i, 0).item:
                            self.removeRow(i)
                            break

    @property
    def selectedReferenceMeta(self) -> Optional[AcqDir]:
        """Returns the ICMetadata that have been selected. Return None if nothing is selected."""
        items: List[ReferencesTableItem] = self.selectedItems()
        assert len(items) <= 1
        if len(items) == 0:
            return None
        else:
            return items[0].item.acqDir

    def _showContextMenu(self, point: QtCore.QPoint):
        items = self.selectedItems()
        if len(items) > 0:
            menu = QMenu("Context Menu")
            refStateString = "Unset as Reference"
            refAction = menu.addAction(refStateString)
            refAction.triggered.connect(
                lambda: self.updateReferences(False, [i.item for i in self.selectedItems()]))
            menu.exec(self.mapToGlobal(point))

    def _clearItems(self):
        self.setRowCount(0)
        self._references = []

