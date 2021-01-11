import dataclasses
import pwspy.dataTypes as pwsdt
from abc import ABC, abstractmethod
import typing
from pwspy.analysis import AbstractAnalysisSettings
from pwspy.analysis.dynamics import DynamicsAnalysisSettings
from pwspy.analysis.pws import PWSAnalysisSettings
from pwspy.dataTypes import MetaDataBase


class AbstractRuntimeAnalysisSettings(ABC):
    """This represents all the information that gets passed to an analysis.
    Unlike AnalysisSettings they can contain objects which are not meant to be saved/loaded.
    This includes the references to the acquisitions to be analyzed as well as the files used
    for calibration and normalization"""

    @abstractmethod
    def getSaveableSettings(self) -> AbstractAnalysisSettings:
        """

        Returns:
            Only the settings which can be saved.
        """
        pass

    @abstractmethod
    def getAnalysisName(self) -> str:
        """

        Returns:
            The name the analysis is referred to by
        """
        pass

    @abstractmethod
    def getReferenceMetadata(self) -> MetaDataBase:
        """

        Returns:
            The metadata object referring to the reference image used for normalization.
        """
        pass

    @abstractmethod
    def getCellMetadatas(self) -> typing.Sequence[MetaDataBase]:
        """

        Returns:
            A sequence of metadata objects for the acquisitions to be analyzed.
        """
        pass

    @abstractmethod
    def getExtraReflectanceMetadata(self) -> typing.Optional[pwsdt.ERMetaData]:
        """

        Returns:
            The metadata object for the extra reflection correction. This can be none if you want to skip this correction.
        """
        pass


@dataclasses.dataclass
class DynamicsRuntimeAnalysisSettings(AbstractRuntimeAnalysisSettings):  # Inherit docstring
    settings: DynamicsAnalysisSettings
    extraReflectanceMetadata: typing.Optional[pwsdt.ERMetaData]
    referenceMetadata: pwsdt.DynMetaData
    cellMetadata: typing.List[pwsdt.DynMetaData]
    analysisName: str

    def getSaveableSettings(self) -> DynamicsAnalysisSettings:  # Inherit docstring
        return self.settings

    def getAnalysisName(self) -> str:
        return self.analysisName

    def getReferenceMetadata(self) -> pwsdt.DynMetaData:
        return self.referenceMetadata

    def getCellMetadatas(self) -> typing.Sequence[pwsdt.DynMetaData]:
        return self.cellMetadata

    def getExtraReflectanceMetadata(self) -> pwsdt.ERMetaData:
        return self.extraReflectanceMetadata


@dataclasses.dataclass
class PWSRuntimeAnalysisSettings(AbstractRuntimeAnalysisSettings):  # Inherit docstring
    settings: PWSAnalysisSettings
    extraReflectanceMetadata: typing.Optional[pwsdt.ERMetaData]
    referenceMetadata: pwsdt.ICMetaData
    cellMetadata: typing.List[pwsdt.ICMetaData]
    analysisName: str

    def getSaveableSettings(self) -> PWSAnalysisSettings:
        return self.settings

    def getAnalysisName(self) -> str:
        return self.analysisName

    def getReferenceMetadata(self) -> pwsdt.ICMetaData:
        return self.referenceMetadata

    def getCellMetadatas(self) -> typing.Sequence[pwsdt.ICMetaData]:
        return self.cellMetadata

    def getExtraReflectanceMetadata(self) -> pwsdt.ERMetaData:
        return self.extraReflectanceMetadata
