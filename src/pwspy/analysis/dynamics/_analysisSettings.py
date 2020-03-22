from __future__ import annotations
import dataclasses
from typing import Optional
from pwspy.analysis import AbstractAnalysisSettings
from pwspy.analysis._abstract import AbstractRuntimeAnalysisSettings
from pwspy.moduleConsts import Material
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes.metadata import ERMetaData


@dataclasses.dataclass
class DynamicsAnalysisSettings(AbstractAnalysisSettings):
    """These settings determine the behavior of the `DynamicsAnalysis` class.
        Args:
            extraReflectanceId: The unique `IDTag` of the extraReflectance calibration that was used on this analysis.
            referenceMaterial: The material that was imaged in the reference image of this analysis. Found as an in pwspy.moduleConst.Material. The
                theoretically predicted
                reflectance of the reference image is used in the extraReflectance correction.
            numericalAperture: The illumination NA of the system. This is used for two purposes. First, we want to make sure that the NA of our data matches
                the NA of our extra reflectance correction cube.
                Second, the theoretically predicted reflectance of our reference is based not only on what our refereMaterial is but also the NA since
                reflectance is angle dependent.
            relativeUnits: If `True` then all calculation are performed such that the reflectance is 1 if it matches the reference. If `False` then we use the
                theoretical reflectance of the reference  (based on NA and reference material) to normalize our results to the actual physical reflectance of
                the sample (about 0.4% for water)
            diffusionRegressionLength: The original matlab scripts for analysis of dynamics data determined the slope of the log(ACF) by looking only at the
                first two indices, (log(ACF)[1]-log(ACF)[0])/dt. This results in very noisy results. However as you at higher index value of the log(ACF) the
                noise becomes much worse. A middle ground is to perform linear regression on the first 4 indices to determine the slope. You can adjust that
                number here.
    """
    extraReflectanceId: str
    referenceMaterial: Material
    numericalAperture: float
    relativeUnits: bool
    diffusionRegressionLength: int = 3

    FileSuffix = "dynAnalysis"  # This is used for saving and loading to json

    def __post_init__(self):
        assert self.diffusionRegressionLength > 0
        assert self.diffusionRegressionLength < 20  # Even 20 is probably way too long, unless a system is created with extremely low noise.

    def _asDict(self) -> dict:
        d = dataclasses.asdict(self)
        if self.referenceMaterial is None:
            d['referenceMaterial'] = None
        else:
            d['referenceMaterial'] = self.referenceMaterial.name  # Convert from enum to string
        return d

    @classmethod
    def _fromDict(cls, d: dict) -> DynamicsAnalysisSettings:
        if d['referenceMaterial'] is not None:
            d['referenceMaterial'] = Material[d['referenceMaterial']]  # Convert from string to enum
        return cls(**d)


@dataclasses.dataclass
class DynamicsRuntimeAnalysisSettings(AbstractRuntimeAnalysisSettings):
    settings: DynamicsAnalysisSettings
    extraReflectanceMetadata: Optional[ERMetaData]

    def getSaveableSettings(self) -> DynamicsAnalysisSettings:
        return self.settings
