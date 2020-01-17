from __future__ import annotations
from ._analysisResults import DynamicsAnalysisResults
from ._analysisSettings import DynamicsAnalysisSettings
from pwspy.analysis import warnings
from pwspy.analysis._abstract import AbstractAnalysis
import numpy as np
from typing import Tuple, List
from pwspy.utility.reflection import reflectanceHelper
from pwspy.moduleConsts import Material
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import DynCube, ExtraReflectanceCube


class DynamicsAnalysis(AbstractAnalysis):
    #TODO this is all untested
    def __init__(self, settings: DynamicsAnalysisSettings, ref: DynCube, extraReflectance: ExtraReflectanceCube):
        super().__init__(settings)
        assert ref.isCorrected()
        ref.normalizeByExposure()
        if ref.metadata.pixelSizeUm is not None:  # Only works if pixel size was saved in the metadata.
            ref.filterDust(.75)  # Apply a blur to filter out dust particles. This is in microns. I'm not sure if this is the optimal value.
        if settings.referenceMaterial is None:
            theoryR = 1  # Having this as 1 effectively ignores it.
            print("Warning: DynamicsAnalysis ignoring reference material correction")
        else:
            theoryR = reflectanceHelper.getReflectance(settings.referenceMaterial, Material.Glass, wavelengths=ref.metadata.wavelength, NA=settings.numericalAperture)
        if extraReflectance is None:
            Iextra = np.zeros(ref.data.shape[:2])  # a bogus reflection that is all zeros
            print("Warning: DynamicsAnalysis ignoring extra reflection")
        else:
            if extraReflectance.metadata.numericalAperture != settings.numericalAperture:
                print(f"Warning: The numerical aperture of your analysis does not match the NA of the Extra Reflectance Calibration. Calibration File NA: {extraReflectance.metadata.numericalAperture}. PWSAnalysis NA: {settings.numericalAperture}.")
            idx = np.asarray(np.array(extraReflectance.wavelengths) == ref.metadata.wavelength).nonzero()[0][0] #The index of extra reflectance that matches the wavelength of our dynamics cube
            I0 = ref.data.mean(axis=2) / (float(theoryR) + extraReflectance.data[:, :, idx]) #  I0 is the intensity of the illumination source, reconstructed in units of `counts`. this is an inversion of our assumption that reference = I0*(referenceReflectance + extraReflectance)
            Iextra = I0 * extraReflectance.data[:, :, idx] #  Convert from reflectance to predicted counts/ms.
        ref.subtractExtraReflection(Iextra)  # remove the extra reflection from our data#
        ref = ref / theoryR[None, None, :]  # now when we normalize by our reference we will get a result in units of physical reflectance rather than arbitrary units.

        self.refMean = ref.data.mean(axis=2)
        self.refAc = ref.getAutocorrelation()
        self.refTag = ref.metadata.idTag
        self.erTag = extraReflectance.metadata.idTag if extraReflectance is not None else None
        self.n_medium = 1.37  # The average index of refraction for chromatin?
        self.settings = settings
        self.extraReflection = Iextra

    def run(self, cube: DynCube) -> Tuple[DynamicsAnalysisResults, List[warnings.AnalysisWarning]]:
        assert cube.isCorrected()
        warns = []
        cube.normalizeByExposure()
        cube.subtractExtraReflection(self.extraReflection)
        cube.normalizeByReference(self.refMean)
        cubeAc = cube.getAutocorrelation()
        rms_t_squared = cubeAc[:, :, 0] - self.refAc[:, :, 0].mean() # The rms^2 noise of the reference averaged over the whole image.
        # If we didn't care about noise subtraction we could get rms_t as just `cube.data.std(axis=2)`

        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)

        #Diffusion
        ac = cubeAc - self.refAc  # Background subtracted autocorrelation function
        ac = ac / ac[:, :, 0][:, :, None]  # Normalize by the zero-lag value
        ac[ac <= 0] = 1e-323  # Before taking the log of the autocorrelation, zero values must be modified to prevent outputs of "inf" or "-inf".
        logac = np.log(ac)

        dt = cube.times[1] - cube.times[0]
        k = (self.n_medium * 2 * np.pi) / cube.metadata.wavelength
        val = logac / (dt * 4 * k ** 2)
        d_slope = -(val[:, :, 1] - val[:, :, 0]) #Get the slope

        results = DynamicsAnalysisResults.create(meanReflectance=reflectance,
                                                 rms_t=np.sqrt(rms_t_squared),
                                                 dSlope=d_slope,
                                                 settings=self.settings,
                                                 imCubeIdTag=cube.metadata.idTag,
                                                 referenceIdTag=self.refTag,
                                                 extraReflectionIdTag=self.erTag)

        return results, warns

