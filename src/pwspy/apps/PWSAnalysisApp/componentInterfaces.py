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
from typing import List, Optional

from PyQt5 import sip

from pwspy import dataTypes as pwsdt


class QABCMeta(sip.wrappertype, abc.ABCMeta):
    pass


class CellSelector(metaclass=QABCMeta):

    @abc.abstractmethod
    def addCell(self, fileName: str, workingDir: str): pass

    @abc.abstractmethod
    def addCells(self, fileNames: List[str], workingDir: str): pass

    @abc.abstractmethod
    def clearCells(self): pass

    @abc.abstractmethod
    def updateFilters(self): pass

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