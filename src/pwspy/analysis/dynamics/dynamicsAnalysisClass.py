from analysis import warnings
from pwspy.analysis._analysisClass import AbstractAnalysis
from pwspy.dataTypes import DynCube

class DynamicsAnalysis(AbstractAnalysis):
    def __init__(self, settings: DynamicsAnalysisSettings, ref: DynCube):
        super().__init__(settings)
        assert ref.isCorrected()
        ref.normalizeByExposure()
        self.refMean = ref.data.mean(axis=2)
        self.refNoise = ref.data.std(axis=2)

    def run(self, cube: DynCube):
        assert cube.isCorrected()
        warns = []
        cube.normalizeByExposure()
        cube.normalizeByReference(self.refMean)
        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)
        warns.append(warnings.checkMeanReflectance(reflectance))
        #Get the autocorrelation of the data
        ac = cube.getAutocorrelation()
        rmsT_sq = (ac - bLim).mean()  # background subtracted sigma_t^2


        # Obtain the RMS of each signal in the cube.
        rms = cube.data.std(axis=2)

