from __future__ import annotations
from abc import ABC, abstractmethod, ABCMeta

import typing
from typing import Optional

from PyQt5.QtCore import QObject

if typing.TYPE_CHECKING:
    from pwspy.analysis import AbstractAnalysisSettings
    from pwspy.dataTypes import CameraCorrection

class QtAbstractMeta(ABCMeta, type(QObject)):
    """Metaclass that allows implementing ABC and QObject simultaneously"""
    pass


class AbstractSettingsFrame(metaclass=QtAbstractMeta):
    @abstractmethod
    def loadFromSettings(self, settings: AbstractAnalysisSettings):
        pass

    @abstractmethod
    def loadCameraCorrection(self, camCorr: Optional[CameraCorrection] = None):
        pass

    @abstractmethod
    def getSettings(self) -> AbstractAnalysisSettings:
        pass

    @abstractmethod
    def getCameraCorrection(self) -> CameraCorrection:
        pass

    @property
    @abstractmethod
    def analysisName(self) -> str:
        pass