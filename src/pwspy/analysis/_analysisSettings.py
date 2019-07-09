from __future__ import annotations
import dataclasses
import json
import os.path as osp
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes._ExtraReflectanceCubeClass import ERMetadata
from pwspy.moduleConsts import Material


@dataclasses.dataclass
class AnalysisSettings:
    filterOrder: int
    filterCutoff: float
    polynomialOrder: int
    extraReflectanceId: str
    referenceMaterial: Material
    wavelengthStart: int
    wavelengthStop: int
    skipAdvanced: bool
    autoCorrStopIndex: int
    autoCorrMinSub: bool  # Determines if the autocorrelation should have it's minimum subtracted from it before processing. These is mathematically nonsense but is needed if the autocorrelation has negative values in it.

    @classmethod
    def fromJson(cls, filePath: str, name: str):
        with open(osp.join(filePath, f'{name}_analysis.json'), 'r') as f:
            d=json.load(f)
        return cls.fromDict(d)

    def toJson(self, filePath: str, name: str):
        d = self.asDict()
        with open(osp.join(filePath, f'{name}_analysis.json'), 'w') as f:
            json.dump(d, f, indent=4)

    def toJsonString(self):
        return json.dumps(self.asDict(), indent=4)

    @classmethod
    def fromJsonString(cls, string: str):
        return cls.fromDict(json.loads(string))

    def asDict(self) -> dict:
        d = dataclasses.asdict(self)
        if self.referenceMaterial is None:
            d['referenceMaterial'] = None
        else:
            d['referenceMaterial'] = self.referenceMaterial.name # Convert from enum to string
        return d

    @classmethod
    def fromDict(cls, d: dict) -> AnalysisSettings:
        if d['referenceMaterial'] is not None:
            d['referenceMaterial'] = Material[d['referenceMaterial']]  # Convert from string to enum
        return cls(**d)
