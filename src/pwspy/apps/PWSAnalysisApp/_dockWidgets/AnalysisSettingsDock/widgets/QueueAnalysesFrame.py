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

from __future__ import annotations
from typing import List, Optional, Tuple
from PyQt5 import QtCore
from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QListWidgetItem, QWidget, QScrollArea, QListWidget, QMessageBox, QMenu, QAction, QDialog, QGridLayout, QPushButton

from pwspy.analysis._abstract import AbstractRuntimeAnalysisSettings
from pwspy.analysis.dynamics import DynamicsRuntimeAnalysisSettings
from pwspy.analysis.pws import PWSRuntimeAnalysisSettings
import typing
if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp._dockWidgets import AnalysisSettingsDock


class AnalysisListItem(QListWidgetItem):
    def __init__(self, settings: AbstractRuntimeAnalysisSettings, parent: Optional[QWidget] = None):
        if isinstance(settings, PWSRuntimeAnalysisSettings):
            prefix = "PWS: "
        elif isinstance(settings, DynamicsRuntimeAnalysisSettings):
            prefix = "DYN: "
        else:
            raise TypeError(f"AnalysisListItem recieve unrecognized analyis settings object of type: {type(settings)}")
        super().__init__(prefix + settings.analysisName, parent)
        self.settings = settings


# noinspection PyUnresolvedReferences
class QueuedAnalysesFrame(QScrollArea):
    def __init__(self, parent: AnalysisSettingsDock):
        super().__init__()
        self.parent = parent
        self.listWidget = QListWidget()
        self.setWidget(self.listWidget)
        self.listWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.listWidget.customContextMenuRequested.connect(self.showContextMenu)
        self.listWidget.setMinimumHeight(30)
        self.setWidgetResizable(True)
        self.listWidget.itemDoubleClicked.connect(self.displayItemSettings)
        self.listWidget.itemClicked.connect(self.highlightAssociatedCells)

    @property
    def analyses(self) -> List[AbstractRuntimeAnalysisSettings]:
        return [self.listWidget.item(i).settings for i in range(self.listWidget.count())]

    def addAnalysis(self, settings: AbstractRuntimeAnalysisSettings):
        item = AnalysisListItem(settings, self.listWidget)  # the item is automatically added to the list here.

    def showContextMenu(self, point: QPoint):
        menu = QMenu("ContextMenu", self)
        deleteAction = QAction("Delete", self)
        deleteAction.triggered.connect(self.deleteSelected)
        menu.addAction(deleteAction)
        deleteAllAction = QAction("Delete All", self)
        deleteAllAction.triggered.connect(self.deleteAll)
        menu.addAction(deleteAllAction)
        menu.exec(self.mapToGlobal(point))

    def deleteSelected(self):
        for i in self.listWidget.selectedItems():
            self.listWidget.takeItem(self.listWidget.row(i))

    def deleteAll(self):
        self.listWidget.clear()

    def highlightAssociatedCells(self, item: AnalysisListItem):
        # Highlight relevant cells
        cellAcq = [cell.acquisitionDirectory for cell in item.settings.cellMetadata]
        refAcq = item.settings.referenceMetadata.acquisitionDirectory
        self.parent._selector.setHighlightedCells(cellAcq)
        self.parent._selector.setHighlightedReference(refAcq)

    def displayItemSettings(self, item: AnalysisListItem):
        # Open a dialog
        message = QMessageBox.information(self, item.settings.analysisName, item.settings.settings.toJsonString())
        # This used to show the settings in a dialog that could be edited. then some changes made it stop working and it was too much work to fix it.
        # d = QDialog(self.parent, (QtCore.Qt.WindowTitleHint | QtCore.Qt.Window))
        # d.setModal(True)
        # d.setWindowTitle(item.name)
        # l = QGridLayout()
        # if item.type == AnalysisTypes.PWS:
        #     settingsFrame = PWSSettingsFrame(self.parent.erManager)
        # elif item.type == AnalysisTypes.DYN:
        #     settingsFrame = DynamicsSettingsFrame(self.parent.erManager)
        # else:
        #     raise TypeError(f"Analysis of type {item.type} is not supported.")
        # settingsFrame.loadFromSettings(item.settings.getSaveableSettings())
        # settingsFrame._analysisNameEdit.setText(item.name)
        # settingsFrame._analysisNameEdit.setEnabled(False)  # Don't allow changing the name.
        #
        # okButton = QPushButton("OK")
        # okButton.released.connect(d.accept)
        #
        # l.addWidget(settingsFrame, 0, 0, 1, 1)
        # l.addWidget(okButton, 1, 0, 1, 1)
        # d.setLayout(l)
        # d.show()
        # d.exec()
        # try:
        #     item.settings = settingsFrame.getSettings()
        # except Exception as e:
        #     QMessageBox.warning(self.parent, 'Oh No!', str(e))



