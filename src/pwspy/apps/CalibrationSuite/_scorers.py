import abc
import typing

import numpy as np
from scipy.signal import correlate
from skimage import measure, metrics

from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.apps.CalibrationSuite.ITOMeasurement import CalibrationResult
from pwspy.utility.misc import cached_property


class Scorer(abc.ABC):
    """
    Compares the 3d reflectance cube of the template with the reflectance cube of a test measurement.
    The test reflectance array should have already been transformed so that they are aligned.
    Any blank section of the transformed test array should be `numpy.nan`

    Args:
        template: A 3d array of reflectance data that the test array will be compared against
        test: A 3d array to compare against the template array. Since it is likely that the original data will need to have been transformed
            in order to align with the template there will blank regions. The pixels in the blank regions should be set to a value of `numpy.nan`
    """
    def __init__(self, template: np.ndarray, test: np.ndarray):
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
    def score(self) -> float:
        tempData = self._template
        testData = self._test
        # Normalize Data. Correlation will pad with 0s so make sure the mean of the data is 0
        tempData = (tempData - tempData.mean()) / tempData.std()
        testData = (testData - testData.mean()) / (testData.std() * testData.size)

        corr = correlate(tempData, testData, mode='same')  # This would be faster if we did mode='valid', there would only be one value. But tiny alignment issues would result it us getting a lower correlation.
        return float(corr.max())


class SSimScorer(Scorer):
    def score(self) -> float:
        tempData = self._template
        testData = self._test
        return float(metrics.structural_similarity(tempData, testData))


class MSEScorer(Scorer):
    def score(self) -> float:
        tempData = self._template
        testData = self._test
        return float(max([1 - metrics.mean_squared_error(tempData, testData), 0]))  # TODO we need a smarter way to convert this to a value between 0 and 1.


class CombinedScorer(Scorer):
    def __init__(self, template: np.ndarray, test: np.ndarray):
        super().__init__(template, test)
        self._mse = MSEScorer(template, test)
        self._ssim = SSimScorer(template, test)
        self._corr = XCorrScorer(template, test)

    @cached_property
    def _scores(self) -> typing.Dict[str, float]:
        """A dictionary containing the score for each scorer contained.
        This is only executed once for each instance of this class, then the cached value is used."""
        return dict(
            mse=self._mse.score(),
            ssim=self._ssim.score(),
            xcorr=self._corr.score()
        )

    def score(self) -> float:
        # TODO not sure how to mix the scores. Just taking the average right now.
        score = 0
        for k, v in self._scores:
            score += v
        return score / len(self._scores)

#
# class CNNScorer(Scorer):
#     pass