import dataclasses
import json
import os.path as osp


@dataclasses.dataclass
class AnalysisSettings:
    filterOrder: int
    filterCutoff: float
    polynomialOrder: int
    extraReflectionPath: str
    referenceMaterial: str
    wavelengthStart: int
    wavelengthStop: int
    skipAdvanced: bool
    useHannWindow: bool
    autoCorrStopIndex: int
    autoCorrMinSub: bool  # Determines if the autocorrelation should have it's minimum subtracted from it before processing. These is mathematically nonsense but is needed if the autocorrelation has negative values in it.

    @classmethod
    def fromJson(cls, filePath: str, name: str):
        with open(osp.join(filePath, f'{name}_analysis.json'), 'r') as f:
            return cls(**json.load(f))

    def toJson(self, filePath: str, name: str):
        with open(osp.join(filePath, f'{name}_analysis.json'), 'w') as f:
            json.dump(dataclasses.asdict(self), f, indent=4)

    def toJsonString(self):
        return json.dumps(dataclasses.asdict(self), indent=4)

    @classmethod
    def fromJsonString(cls, string: str):
        return cls(**json.loads(string))
