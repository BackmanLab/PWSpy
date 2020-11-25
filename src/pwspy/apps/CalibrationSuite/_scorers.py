import abc

import numpy as np
from scipy.signal import correlate
from skimage import measure, metrics

from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.apps.CalibrationSuite.ITOMeasurement import CalibrationResult


class Scorer(abc.ABC):
    """
    Compares the 3d reflectance cube of the template with the reflectance cube of a test measurement.
    The test reflectance array should have already been transformed so that they are aligned.
    Any blank section of the transformed test array should be `numpy.nan` # TODO cropping

    Args:
        template: A 3d array of reflectance data that the test array will be compared against
        test: A 3d array to compare agains the template array. Since it is likely that the original data will need to have been transformed
            in order to align with the template there will blank regions. The pixels in the blank regions should be set to a value of `numpy.nan`
    """
    def __init__(self, template: PWSAnalysisResults, test: CalibrationResult):
        assert isinstance(template, PWSAnalysisResults)
        assert isinstance(test, CalibrationResult)
        self._template = template.reflectance.data + template.meanReflectance[:, :, None]
        self._test = test

    @abc.abstractmethod
    def score(self) -> float:
        """

        Returns:
            A value between 0 and 1 indicating how well this scorer rates the match between the template and the test array.
        """
        pass


class XCorrScorer(Scorer):
    def score(self) -> float:
        slc = self._test.getValidDataSlice()  # This slice is used to crop out any NAN regions from the data since these will mess up the x-correlation
        tempData = self._template[slc]
        testData = self._test.transformedData[slc]
        # Normalize Data. Correlation will pad with 0s so make sure the mean of the data is 0
        tempData = (tempData - tempData.mean()) / tempData.std()
        testData = (testData - testData.mean()) / (testData.std() * testData.size)

        corr = correlate(tempData, testData, mode='same')  # This would be faster if we did mode='valid', there would only be one value. But tiny alignment issues would result it us getting a lower correlation.
        return corr.max()


class SSimScorer(Scorer):
    def score(self) -> float:
        slc = self._test.getValidDataSlice()
        tempData = self._template[slc]
        testData = self._test.transformedData[slc]
        return metrics.structural_similarity(tempData, testData)


class MSEScorer(Scorer):
    def score(self) -> float:
        slc = self._test.getValidDataSlice()
        tempData = self._template[slc]
        testData = self._test.transformedData[slc]
        return metrics.mean_squared_error(tempData, testData)
#
# class CNNScorer(Scorer):
#     pass