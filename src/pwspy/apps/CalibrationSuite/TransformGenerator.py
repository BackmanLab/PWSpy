from __future__ import annotations
import enum
import time
import typing

import numpy as np
import logging

from pwspy.analysis import pws as pwsAnalysis
from pwspy.utility.machineVision import ORBRegisterTransform, SIFTRegisterTransform, crossCorrelateRegisterTranslation


class TransformGenerator:
    """
    Uses a feature matching algorithm to generate the affine transform between some data and a template data array.

    Args:
        template: The PWS analysis results to be used as a template. We will try to find the transform that matches our data to this template.
        method: Selects which method to use for generating affine transformations between images.
        debugMode: If `True` then some plots will be opened to help with understanding the performance of the feature matcher.
    """
    def __init__(self, template: pwsAnalysis.PWSAnalysisResults, method: TransformGenerator.Method = None, debugMode: bool = False):
        if method == TransformGenerator.Method.SIFT or method is None:
            self._matcherFunc = SIFTRegisterTransform
        elif method == TransformGenerator.Method.ORB:
            self._matcherFunc = ORBRegisterTransform
        elif method == TransformGenerator.Method.XCORR:
            self._matcherFunc = crossCorrelateRegisterTranslation
        else:
            raise ValueError(f"TransformGenerator method {method} is not supported.")
        self._method = method
        self._debugMode = debugMode
        self._template = template
        self._debugAnimationRef = None  # Just a reference used to keep the animation alive.

    def getMethodName(self) -> str:
        return self._method.name

    def match(self, ims: typing.Iterable[pwsAnalysis.PWSAnalysisResults]) -> typing.Iterable[np.ndarray]:
        """Run feature matching on a set of data.

        Args:
            ims: An iterable of PWS analysis results. This funciton will return the affine transformation between the template and each of these analysis results.
        """
        logger = logging.getLogger(__name__)
        matchTime = time.time()
        logger.debug("Start match.")
        trans, self._debugAnimationRef = self._matcherFunc(self._template.meanReflectance, [im.meanReflectance for im in ims], debugPlots=self._debugMode)
        logger.debug(f"Image matching took {time.time() - matchTime} seconds")
        return trans

    class Method(enum.Enum):
        SIFT = "Slow but generally more successful than ORB"
        ORB = "Faster than SIFT and usually good enough"
        XCORR = "Doesn't support rotation or scale changes, only translation. Very fast and accurate."
