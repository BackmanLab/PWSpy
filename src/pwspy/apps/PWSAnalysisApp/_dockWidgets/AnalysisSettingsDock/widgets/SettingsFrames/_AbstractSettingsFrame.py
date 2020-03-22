from __future__ import annotations
from abc import ABC, abstractmethod, ABCMeta

import typing
from typing import Optional

from PyQt5.QtCore import QObject

from pwspy.analysis._abstract import AbstractRuntimeAnalysisSettings

if typing.TYPE_CHECKING:
    from pwspy.analysis import AbstractAnalysisSettings
    from pwspy.dataTypes import CameraCorrection
    from pwspy.dataTypes.metadata import ERMetaData


class QtAbstractMeta(ABCMeta, type(QObject)):
    """Metaclass that allows implementing ABC and QObject simultaneously"""
    pass


class AbstractSettingsFrame(metaclass=QtAbstractMeta):
    @abstractmethod
    def loadFromSettings(self, settings: AbstractAnalysisSettings):
        """Populate the UI so that they match `settings`"""
        pass

    @abstractmethod
    def loadCameraCorrection(self, camCorr: Optional[CameraCorrection] = None):
        """Populate the UI to match the `camCorr` camera correction"""
        pass


    @abstractmethod
    def getSettings(self) -> AbstractRuntimeAnalysisSettings:
        """Generate a new settings object based on the current state of the UI"""
        pass

    @abstractmethod
    def getCameraCorrection(self) -> Optional[CameraCorrection]:
        """Generate a new CameraCorrection based on the current state of the UI.
        Return None for auto detected camera correction"""
        pass


    @property
    @abstractmethod
    def analysisName(self) -> str:
        """Get the name that the user has chosen to save this analysis as."""
        pass