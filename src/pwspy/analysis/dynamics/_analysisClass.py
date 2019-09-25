from analysis.dynamics._analysisResults import DynamicsAnalysisResults
from pwspy.analysis import warnings
from pwspy.analysis._abstract import AbstractAnalysis
from ._analysisSettings import DynamicsAnalysisSettings
from pwspy.dataTypes import DynCube, ExtraReflectanceCube
import numpy as np
from typing import Tuple, List

class DynamicsAnalysis(AbstractAnalysis):
    #TODO subtract single wavelength from extraReflection for ref and cube
    def __init__(self, settings: DynamicsAnalysisSettings, ref: DynCube, extraReflectance: ExtraReflectanceCube):
        super().__init__(settings)
        assert ref.isCorrected()
        ref.normalizeByExposure()
        self.refMean = ref.data.mean(axis=2)
        self.refNoise = ref.getAutocorrelation()[:, :, 0].mean() # The rms^2 noise of the reference averaged over the whole image.
        self.refTag = ref.metadata.idTag
        self.erTag = extraReflectance.metadata.idTag
        self.n_medium = 1.37 #The average index of refraction for chromatin
        self.settings = settings

    def run(self, cube: DynCube) -> Tuple[DynamicsAnalysisResults, List[warnings.AnalysisWarning]]:
        assert cube.isCorrected()
        warns = []
        cube.normalizeByExposure()
        cube.normalizeByReference(self.refMean)
        rms_t_squared = cube.getAutocorrelation()[:, :, 0] - self.refNoise
        # If we didn't care about noise subtraction we could get rms_t as just `cube.data.std(axis=2)`
        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)
        warns.append(warnings.checkMeanReflectance(reflectance))

        results = DynamicsAnalysisResults.create(meanReflectance=reflectance,
                                                 rms_t=np.sqrt(rms_t_squared),
                                                 settings=self.settings,
                                                 imCubeIdTag=cube.metadata.idTag,
                                                 referenceIdTag=self.refTag,
                                                 extraReflectionIdTag=self.erTag)

        return results, warns
