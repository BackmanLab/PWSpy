from __future__ import annotations

from multiprocessing.sharedctypes import RawArray
from numpy import ma

from ._analysisResults import DynamicsAnalysisResults
from ._analysisSettings import DynamicsAnalysisSettings, DynamicsRuntimeAnalysisSettings
from pwspy.analysis import warnings
from pwspy.analysis._abstract import AbstractAnalysis
import numpy as np
import pandas as pd
from typing import Tuple, List
from pwspy.utility.reflection import reflectanceHelper
from pwspy.moduleConsts import Material
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import DynCube


class DynamicsAnalysis(AbstractAnalysis):
    """This class performs the analysis of RMS_t_squared and D described in the paper: "Multimodal interferometric imaging of nanoscale structure and
    macromolecular motion uncovers UV induced cellular paroxysm". It is based on a set of matlab scripts written by the author of that paper, Scott Gladstein.
     The original scripts can be found in the `_oldMatlab` subpackage."""
    def __init__(self, settings: DynamicsRuntimeAnalysisSettings, ref: DynCube):
        super().__init__()
        from pwspy.dataTypes import ExtraReflectanceCube
        extraReflectance = ExtraReflectanceCube.fromMetadata(settings.extraReflectanceMetadata) if settings.extraReflectanceMetadata is not None else None
        settings = settings.getSaveableSettings()
        assert ref.processingStatus.cameraCorrected
        ref.normalizeByExposure()
        if ref.metadata.pixelSizeUm is not None:  # Only works if pixel size was saved in the metadata.
            ref.filterDust(.75)  # Apply a blur to filter out dust particles. This is in microns. I'm not sure if this is the optimal value.
        if settings.referenceMaterial is None:
            theoryR = pd.Series(np.ones((len(ref.times),)), index=ref.times)  # Having this as all ones effectively ignores it.
            print("Warning: DynamicsAnalysis ignoring reference material correction")
        else:
            theoryR = reflectanceHelper.getReflectance(settings.referenceMaterial, Material.Glass, wavelengths=ref.metadata.wavelength, NA=settings.numericalAperture)
        if extraReflectance is None:
            Iextra = None  # a bogus reflection that is all zeros
            print("Warning: DynamicsAnalysis ignoring extra reflection")
        else:
            if extraReflectance.metadata.numericalAperture != settings.numericalAperture:
                print(f"Warning: The numerical aperture of your analysis does not match the NA of the Extra Reflectance Calibration. Calibration File NA: {extraReflectance.metadata.numericalAperture}. PWSAnalysis NA: {settings.numericalAperture}.")
            idx = np.asarray(np.array(extraReflectance.wavelengths) == ref.metadata.wavelength).nonzero()[0][0] #The index of extra reflectance that matches the wavelength of our dynamics cube
            I0 = ref.data.mean(axis=2) / (float(theoryR) + extraReflectance.data[:, :, idx]) #  I0 is the intensity of the illumination source, reconstructed in units of `counts`. this is an inversion of our assumption that reference = I0*(referenceReflectance + extraReflectance)
            Iextra = I0 * extraReflectance.data[:, :, idx] #  Convert from reflectance to predicted counts/ms.
            ref.subtractExtraReflection(Iextra)  # remove the extra reflection from our data#
        if not settings.relativeUnits:
            ref = ref / theoryR[None, None, :]  # now when we normalize by our reference we will get a result in units of physical reflectance rather than arbitrary units.

        self.refMean = ref.data.mean(axis=2)
        ref.normalizeByReference(self.refMean)  # We normalize so that the average is 1. This is for scaling purposes with the AC. Seems like the AC should be scale independent though, not sure.
        self.refAc = ref.getAutocorrelation()[:, :, :settings.diffusionRegressionLength+1].mean(axis=(0, 1))  # We find the average autocorrlation of the background to cut down on noise, presumably this is uniform accross the field of view any way, right?
        self.refTag = ref.metadata.idTag
        self.erTag = extraReflectance.metadata.idTag if extraReflectance is not None else None
        self.n_medium = 1.37  # The average index of refraction for chromatin?
        self.settings = settings
        self.extraReflection = Iextra

    def run(self, cube: DynCube) -> Tuple[DynamicsAnalysisResults, List[warnings.AnalysisWarning]]:
        assert cube.processingStatus.cameraCorrected
        warns = []
        cube.normalizeByExposure()
        if self.extraReflection is not None:
            cube.subtractExtraReflection(self.extraReflection)
        cube.normalizeByReference(self.refMean)

        cubeAc = cube.getAutocorrelation()
        cubeAc = cubeAc[:, :, :self.settings.diffusionRegressionLength+1] # We are only going to use the first few time points of the ACF, we can get rid of the rest.
        rms_t_squared = cubeAc[:, :, 0] - self.refAc[0]  # The rms^2 noise of the reference averaged over the whole image.
        rms_t_squared[rms_t_squared < 0] = 0  # Sometimes the above noise subtraction can cause some of our values to be barely below 0, that's going to be a problem.
        # If we didn't care about noise subtraction we could get rms_t as just `cube.data.std(axis=2)`

        # Determine the mean-reflectance for each pixel in the cell.
        reflectance = cube.data.mean(axis=2)

        #Diffusion
        cubeAc = ma.array(cubeAc) # Convert to the numpy.MaskedArray type to help us mark some data as invalid.
        cubeAc[cubeAc.data[:, :, 0] < np.sqrt(2)*self.refAc[0]] = ma.masked # Remove pixels with low SNR. Default threshold removes values where 1st point of acf is less than sqrt(2) of background acf
        ac = ma.array(cubeAc - self.refAc)  # Background subtracted autocorrelation function.
        ac = ac / ac[:, :, 0][:, :, None]  # Normalize by the zero-lag value
        ac[np.any(ac <= 0, axis=2)] = ma.masked  # Before taking the log of the autocorrelation any negative or zero values will cause problems. Remove the pixel entirely

        dt = (cube.times[-1] - cube.times[0]) / (len(cube.times) - 1) / 1e3  # Convert to seconds
        k = (self.n_medium * 2 * np.pi) / (cube.metadata.wavelength / 1e3)  # expressing wavelength in microns to match up with old matlab code.
        val = np.log(ac) / (4 * k ** 2) # See the `theory` section of the paper for an explanation of the 4k^2. The slope of log(ac) should be equivalent to 1/t_c in the paper.
        d_slope = -self._maskedLinearRegression(val, dt) # Get the slope of the autocorrelation. This is related to the diffusion in the cell. The minus is here to make the number positive, the slope is really negative.

        results = DynamicsAnalysisResults.create(meanReflectance=reflectance,
                                                 rms_t_squared=rms_t_squared,
                                                 reflectance=cube,
                                                 diffusion=d_slope,
                                                 settings=self.settings,
                                                 imCubeIdTag=cube.metadata.idTag,
                                                 referenceIdTag=self.refTag,
                                                 extraReflectionIdTag=self.erTag)

        return results, warns

    @staticmethod
    def _maskedLinearRegression(arr: ma.MaskedArray, dt: float):
        """Takes a 3d ACF array as input and returns a 2d array indicating the slope along the 3rd dimension of the input array.
         The dimensions of the output array match the first two dimensions of the input array. The input array can have invalid pixels masked out, this function
         will exclude them from the calculation."""
        origShape = arr.shape
        y = np.reshape(arr, (origShape[0]*origShape[1], origShape[2]))  #Convert to a 2d array [pixels, time]. This is required by the polyfit function.
        t = np.array([i*dt for i in range(origShape[2])]) # Generate a 1d array representing the time axis.
        # Y = np.reshape(y[~y.mask], (np.sum((~y.mask).sum()//y.shape[1], y.shape[1])))  # Remove all the masked pixels since the polyfit function doesn't know what to do with them.
        Y = np.reshape(y[~y.mask], ((~y.mask).sum()//y.shape[1], y.shape[1]))  # Remove all the masked pixels since the polyfit function doesn't know what to do with them.
        coeff = np.polyfit(t, Y.T, deg=1)  # Linear fit
        slope = coeff[0, :]  # Get the slope and ignore the y intercept
        Slope = ma.zeros(y.shape[0]) # Create an empty masked array that includes all pixels again
        Slope.mask = y.mask[:, 0] # Copy the original mask indicating which pixels are invalid.
        Slope[~Slope.mask] = slope  # Fill our calculated slopes into the yunmasked pixels.
        Slope = np.reshape(Slope, (origShape[0], origShape[1])) # Reshape back to a 2d image
        return Slope

    def copySharedDataToSharedMemory(self):
        refdata = RawArray('f', self.refAc.size)
        refdata = np.frombuffer(refdata, dtype=np.float32).reshape(self.refAc.shape)
        np.copyto(refdata, self.refAc)
        self.refAc = refdata

        refmdata = RawArray('f', self.refMean.size)
        refmdata = np.frombuffer(refmdata, dtype=np.float32).reshape(self.refMean.shape)
        np.copyto(refmdata, self.refMean)
        self.refMean = refmdata

        if self.extraReflection is not None:
            iedata = RawArray('f', self.extraReflection.size)
            iedata = np.frombuffer(iedata, dtype=np.float32).reshape(self.extraReflection.shape)
            np.copyto(iedata, self.extraReflection)
            self.extraReflection = iedata
