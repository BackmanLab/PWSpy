import abc
import logging
import typing
import numpy as np
import scipy.signal as sps
from skimage import metrics
from pwspy.utility.misc import cached_property
from time import time

#TODO device a way to inject a cube splitter into a scorer for more efficient high granularity socring

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
    def score(self) -> dict:
        """

        Returns:
            A dictionary of scoring information including one value under the name 'score' which is between 0 and 1 indicating how well this scorer rates the match between the template and the test array.
        """
        pass


class XCorrScorer(Scorer):  # Terrible performance, don't use.
    def score(self) -> float:
        tempData = self._template
        testData = self._test
        # Normalize Data. Correlation will pad with 0s so make sure the mean of the data is 0
        tempData = (tempData - tempData.mean()) / tempData.std()
        testData = (testData - testData.mean()) / (testData.std() * testData.size)

        corr = sps.correlate(tempData, testData, mode='same')  # This would be faster if we did mode='valid', there would only be one value. But tiny alignment issues would result it us getting a lower correlation.
        assert not np.any(np.isnan(corr)), "NaN values found in XCorrScorer"
        return float(corr.max())


class LateralXCorrScorer(Scorer):
    def score(self) -> dict:
        # Select a single wavelength image from the middle of the array.
        tempData = self._template[:, :, self._template.shape[2]//2]
        testData = self._test[:, :, self._test.shape[2]//2]

        # Normalize Data. Correlation will pad with 0s so make sure the mean of the data is 0
        tempData = (tempData - tempData.mean()) / tempData.std()
        testData = (testData - testData.mean()) / (testData.std() * testData.size)  # The division by testData.size here gives us a final xcorrelation that maxes out at 1.
        corr = sps.correlate(tempData, testData, mode='full')  # Using 'full' here instead of 'same' means that we can reliably know the index of the zero-shift element of the output
        zeroShiftIdx = (corr.shape[0]//2, corr.shape[1]//2)
        peakIdx = np.unravel_index(corr.argmax(), corr.shape)
        cdrY, cdrX = self._calculate2DCDR(corr, peakIdx, 2)
        return {'score': float(corr.max()), 'shift': (peakIdx[0]-zeroShiftIdx[0], peakIdx[1]-zeroShiftIdx[1]), 'cdrY': cdrY, 'cdrX': cdrX}

    @staticmethod
    def _calculate2DCDR(corr: np.ndarray, peakIdx: typing.Tuple[int, int], interval: int) -> typing.Tuple[float, float]:
        corrY = corr[:, peakIdx[1]]
        cdr1 = (corrY[peakIdx[0]] - corrY[peakIdx[0] + interval]) / interval
        cdr2 = (corrY[peakIdx[0]] - corrY[peakIdx[0] - interval]) / interval
        cdrY = (cdr2 + cdr1) / 2  # Take the average of the cdr in each direction

        corrX = corr[peakIdx[0], :]
        cdr1 = (corrX[peakIdx[1]] - corrX[peakIdx[1] + interval]) / interval  # In decay per pixel offset
        cdr2 = (corrX[peakIdx[1]] - corrX[peakIdx[1] - interval]) / interval
        cdrX = (cdr2 + cdr1) / 2  # Take the average of the cdr in each direction
        return cdrY, cdrX


class AxialXCorrScorer(Scorer):
    def score(self) -> dict:
        tempData = self._template
        testData = self._test
        #Normalize Each XY pixel sso that the xcorrelation hasa max of 1.
        tempData = (tempData - tempData.mean(axis=2)[:, :, None]) / tempData.std(axis=2)[:, :, None]
        testData = (testData - testData.mean(axis=2)[:, :, None]) / (
                    testData.std(axis=2)[:, :, None] * testData.shape[2])  # The division by testData.size here gives us a final xcorrelation that maxes out at 1.

        #Very hard to find support for 1d correlation on an Nd array. scipy.signal.fftconvolve appears to be the best option
        corr = sps.fftconvolve(tempData, self._reverse_and_conj(testData), axes=2, mode='full')
        corr = corr.mean(axis=(0, 1))
        zeroShiftIdx = corr.shape[0]//2
        peakIdx = corr.argmax()
        cdr = self._calculate1DCDR(corr, peakIdx, 2)
        return {'score': float(corr.max()), 'shift': (peakIdx[0]-zeroShiftIdx[0], peakIdx[1]-zeroShiftIdx[1]), 'cdr': cdr}

    @staticmethod
    def _reverse_and_conj(x):
        """
        Reverse array `x` in all dimensions and perform the complex conjugate.
        Copied from scipy.signal, This makes a convolution effectively a correlation. Modified to only effect the 2nd axis
        """
        return x[:, :, ::-1].conj()

    @staticmethod
    def _calculate1DCDR(corr: np.ndarray, peakIdx: int, interval: int) -> float:
        cdr1 = (corr[peakIdx] - corr[peakIdx + interval]) / interval
        cdr2 = (corr[peakIdx] - corr[peakIdx - interval]) / interval
        return (cdr2 + cdr1) / 2  # Take the average of the cdr in each direction


class SSimScorer(Scorer):
    def score(self) -> dict:
        tempData = self._template
        testData = self._test
        score = float(metrics.structural_similarity(tempData, testData))
        assert not np.isnan(score), "NaN value found in SSimScorer"
        return {'score': score}


class MSEScorer(Scorer):
    def score(self) -> dict:
        tempData = self._template
        testData = self._test
        mse = metrics.mean_squared_error(tempData, testData)  # TODO we need a smarter way to convert this to a value between 0 and 1.
        assert not np.isnan(mse), "NaN value found in MSEScorer"
        nmse = mse / (tempData**2).sum()
        return {'score': nmse, 'mse': mse}


class CombinedScorer(Scorer):
    def __init__(self, template: np.ndarray, test: np.ndarray):
        super().__init__(template, test)
        self._mse = MSEScorer(template, test)
        self._ssim = SSimScorer(template, test)
        self._latCorr = LateralXCorrScorer(template, test)
        self._axCorr = AxialXCorrScorer(template, test)

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
        latxcorr = self._latCorr.score()
        logger.debug(f"LatXCORR score took {time() - t}")
        t = time()
        axxcorr = self._axCorr.score()
        logger.debug(f"AxXCORR score took {time() - t}")
        return dict(
            mse=mse,
            ssim=ssim,
            latxcorr=latxcorr,
            axxcorr=axxcorr
        )

    def score(self) -> dict:
        # TODO not sure how to mix the scores. Just taking the average right now.
        score = 0
        for k, v in self._scores:
            score += v['score']
        return {'score': score / len(self._scores), 'details': self._scores}

#
# class CNNScorer(Scorer):
#     pass