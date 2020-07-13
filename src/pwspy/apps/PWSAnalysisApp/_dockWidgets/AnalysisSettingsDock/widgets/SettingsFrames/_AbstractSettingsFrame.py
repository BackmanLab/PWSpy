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
from abc import ABC, abstractmethod, ABCMeta

import typing
from typing import Optional

from PyQt5.QtCore import QObject

from pwspy.analysis import AbstractRuntimeAnalysisSettings

if typing.TYPE_CHECKING:
    from pwspy.analysis import AbstractAnalysisSettings

class QtAbstractMeta(ABCMeta, type(QObject)):
    """Metaclass that allows implementing ABC and QObject simultaneously"""
    pass


class AbstractSettingsFrame(metaclass=QtAbstractMeta):
    @abstractmethod
    def loadFromSettings(self, settings: AbstractAnalysisSettings):
        """Populate the UI so that they match `settings`"""
        pass

    @abstractmethod
    def getSettings(self) -> AbstractRuntimeAnalysisSettings:
        """Generate a new settings object based on the current state of the UI"""
        pass
