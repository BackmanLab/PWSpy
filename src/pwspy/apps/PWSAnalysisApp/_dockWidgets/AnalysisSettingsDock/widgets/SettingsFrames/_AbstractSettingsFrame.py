from __future__ import annotations
from abc import ABC, abstractmethod

import typing

if typing.TYPE_CHECKING:
    from pwspy.analysis import AbstractAnalysisSettings
    from pwspy.dataTypes import CameraCorrection


class AbstractSettingsFrame(ABC):
    @abstractmethod
    def loadFromSettings(self, settings: AbstractAnalysisSettings):
        pass

    @abstractmethod
    def getSettings(self) -> AbstractAnalysisSettings:
        pass

    @abstractmethod
    def getCameraCorrection(self) -> CameraCorrection:
        pass

    @abstractmethod
    @property
    def analysisName(self) -> str:
        pass