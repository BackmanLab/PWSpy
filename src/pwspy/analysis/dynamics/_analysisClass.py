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
        self.refAc = ref.getAutocorrelation()
        self.refTag = ref.metadata.idTag
        self.erTag = extraReflectance.metadata.idTag
        self.n_medium = 1.37  # The average index of refraction for chromatin
        self.settings = settings

    def run(self, cube: DynCube) -> Tuple[DynamicsAnalysisResults, List[warnings.AnalysisWarning]]:
        assert cube.isCorrected()
        warns = []
        cube.normalizeByExposure()
        cube.normalizeByReference(self.refMean)
        cubeAc = cube.getAutocorrelation()
        rms_t_squared = cubeAc[:, :, 0] - self.refAc[:, :, 0].mean() # The rms^2 noise of the reference averaged over the whole image.
        # If we didn't care about noise subtraction we could get rms_t as just `cube.data.std(axis=2)`
        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)
        warns.append(warnings.checkMeanReflectance(reflectance))

        #Diffusion
        ac = cubeAc - self.refAc  # Background subtracted autocorrelation function
        ac = ac / ac[:, :, 0]  # Normalize by the zero-lag value
        ac[ac <= 0] = 1e-323  # Before taking the log of the autocorrelation, zero values must be modified to prevent outputs of "inf" or "-inf".
        logac = np.log(ac)

        dt = cube.times[1] - cube.times[0]
        k = (self.n_medium * 2 * np.pi) / cube.metadata.wavelength
        val = logac / (dt * 4 * k ^ 2)
        d_slope = -(val[:, :, 1] - val[:, :, 0]) #Get the slope

        results = DynamicsAnalysisResults.create(meanReflectance=reflectance,
                                                 rms_t=np.sqrt(rms_t_squared),
                                                 dSlope=d_slope,
                                                 settings=self.settings,
                                                 imCubeIdTag=cube.metadata.idTag,
                                                 referenceIdTag=self.refTag,
                                                 extraReflectionIdTag=self.erTag)

        return results, warns
