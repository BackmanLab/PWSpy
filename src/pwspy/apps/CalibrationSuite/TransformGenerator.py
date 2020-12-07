import time
import typing

import numpy as np
import logging

from pwspy.analysis import pws as pwsAnalysis
from pwspy.utility.machineVision import ORBRegisterTransform, SIFTRegisterTransform


class TransformGenerator:
    """
    Uses a feature matching algorithm to generate the affine transform between some data and a template data array.

    Args:
        template: The PWS analysis results to be used as a template. We will try to find the transform that matches our data to this template.
        fastMode: If `True` then used the ORB algorithm for feature matching rather than SIFT. This is much faster but may not be as reliable.
        debugMode: If `True` then some plots will be opened to help with understanding the performance of the feature matcher.
    """
    def __init__(self, template: pwsAnalysis.PWSAnalysisResults, fastMode: bool = False, debugMode: bool = False):
        self._matcherFunc = ORBRegisterTransform if fastMode else SIFTRegisterTransform
        self._debugMode = debugMode
        self._template = template
        self._debugAnimationRef = None  # Just used to keep the animation alive.

    def match(self, ims: typing.Iterable[pwsAnalysis.PWSAnalysisResults]) -> typing.Iterable[np.ndarray]:
        """Run feature matching on a set of data.

        Args:
            ims: An iterable of PWS analysis results. This funciton will return the affine transformation between the template and each of these analysis results.
        """
        logger = logging.getLogger(__name__)
        matchTime = time.time()
        logger.debug("Start match.")
        trans, self._debugAnimationRef = self._matcherFunc(self._template.meanReflectance, [im.meanReflectance for im in ims], debugPlots=self._debugMode)
        logger.debug(f"Matching took {time.time() - matchTime} seconds")
        return trans
    