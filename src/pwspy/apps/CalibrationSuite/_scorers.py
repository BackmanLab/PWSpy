import abc
import logging
import typing
import numpy as np
import scipy.signal as sps
from skimage import metrics
from pwspy.utility.misc import cached_property
from time import time


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
        testData = (testData - testData.mean()) / (testData.std() * testData.size)  # The division by testData.size here gives us a final xcorrelation that maxes out at 1.

        #Using mode='same' takes too much memory and too much time, but we still want to be aable to examing how the xcorrelation is shifted from 0.
        #We manually pad one array with zeros and use mode='valid' to manually select how far out to calculate the xcorrelation
        padding = (5, 5, 10)  # ypad, xpad, zpad, padding of this length will be added on each size of each axis. The final shape of the correlation output will be 2 * n + 1
        padding = tuple((i, i) for i in padding)# Translate the padding tuple to a form understood by numpy
        tempData = np.pad(tempData, padding)  # 0 padding.
        import time
        stime = time.time()
        corr = sps.correlate(tempData, testData, mode='valid')  # This would be faster if we did mode='valid', there would only be one value. But tiny alignment issues would result it us getting a lower correlation.
        ftime = time.time() - stime
        print(ftime)
        assert not np.any(np.isnan(corr)), "NaN values found in XCorrScorer"
        return float(corr.max())


class SSimScorer(Scorer):
    def score(self) -> float:
        tempData = self._template
        testData = self._test
        score = float(metrics.structural_similarity(tempData, testData))
        assert not np.isnan(score), "NaN value found in SSimScorer"
        return score


class MSEScorer(Scorer):
    def score(self) -> float:
        tempData = self._template
        testData = self._test
        score = metrics.mean_squared_error(tempData, testData)  # TODO we need a smarter way to convert this to a value between 0 and 1.
        assert not np.isnan(score), "NaN value found in MSEScorer"
        return score


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
        logger = logging.getLogger(__name__)
        t = time()
        mse = self._mse.score()
        logger.debug(f"MSE score took {time() - t}")
        t = time()
        ssim = self._ssim.score()
        logger.debug(f"SSIM score took {time() - t}")
        t = time()
        xcorr = self._corr.score()
        logger.debug(f"XCORR score took {time() - t}")
        return dict(
            mse=mse,
            ssim=ssim,
            xcorr=xcorr
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