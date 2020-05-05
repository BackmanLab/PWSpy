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
