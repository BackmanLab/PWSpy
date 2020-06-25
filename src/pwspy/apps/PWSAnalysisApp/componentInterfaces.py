# Copyright © 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
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

"""

@author: Nick Anthony
"""
import abc
import typing
from typing import List, Optional

import sip
from PyQt5.QtWidgets import QWidget

from pwspy import dataTypes as pwsdt
from pwspy.analysis import AbstractRuntimeAnalysisSettings
from pwspy.apps.PWSAnalysisApp.utilities.conglomeratedAnalysis import ConglomerateCompilerResults, \
    ConglomerateCompilerSettings


class QABCMeta(sip.wrappertype, abc.ABCMeta):
    pass


class CellSelector(metaclass=QABCMeta):
    @abc.abstractmethod
    def loadNewCells(self, fileNames: List[str], workingDir: str): pass

    @abc.abstractmethod
    def getSelectedCellMetas(self) -> List[pwsdt.AcqDir]: pass

    @abc.abstractmethod
    def getAllCellMetas(self) -> List[pwsdt.AcqDir]: pass

    @abc.abstractmethod
    def getSelectedReferenceMeta(self) -> Optional[pwsdt.AcqDir]: pass

    @abc.abstractmethod
    def setSelectedCells(self, cells: List[pwsdt.AcqDir]): pass

    @abc.abstractmethod
    def setSelectedReference(self, ref: pwsdt.AcqDir): pass

    @abc.abstractmethod
    def setHighlightedCells(self, cells: List[pwsdt.AcqDir]): pass

    @abc.abstractmethod
    def setHighlightedReference(self, ref: pwsdt.AcqDir): pass

    @abc.abstractmethod
    def refreshCellItems(self): pass


class ResultsTableController(metaclass=QABCMeta):
    @abc.abstractmethod
    def addCompilationResult(self, result: ConglomerateCompilerResults, acquisition: pwsdt.AcqDir): pass

    @abc.abstractmethod
    def clearCompilationResults(self): pass

    @abc.abstractmethod
    def getSettings(self) -> ConglomerateCompilerSettings: pass

    @abc.abstractmethod
    def getRoiName(self) -> str: pass

    @abc.abstractmethod
    def getAnalysisName(self) -> str: pass


class AnalysisSettingsCreator(metaclass=QABCMeta):
    @abc.abstractmethod
    def getListedAnalyses(self) -> typing.List[AbstractRuntimeAnalysisSettings]: pass
