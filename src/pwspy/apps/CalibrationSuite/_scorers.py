import abc

import numpy as np
from scipy.signal import correlate

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
    def __init__(self, template: np.ndarray, test: CalibrationResult):
        assert isinstance(template, np.ndarray)
        assert isinstance(test, CalibrationResult)
        self._template = template
        self._test = test

    @abc.abstractmethod
    def score(self) -> float:
        """

        Returns:
            A value between 0 and 1 indicating how well this scorer rates the match between the template and the test array.
        """
        pass


class XCorrScorer(Scorer):
    def __init__(self, template: np.ndarray, test: CalibrationResult):
        super().__init__(template, test)

    def score(self):
        slc = self._test.getValidDataSlice()

        corr = correlate(self._template[slc], self._test.transformedData[slc])  #Need to crop the nan regions
        return corr
    # TODO measure average spectrum over a fine grid of the transformed image.
    # TODO calculate 3d cross correlation function and measure slope in various directions.

# class SSimScorer(Scorer):
#     pass
#
#
# class MSEScorer(Scorer):
#     pass
#
#
# class CNNScorer(Scorer):
#     pass