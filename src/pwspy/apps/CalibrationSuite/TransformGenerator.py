import time
import typing

import numpy as np
import logging

from pwspy.analysis import pws as pwsAnalysis
from pwspy.utility.machineVision import ORBRegisterTransform, SIFTRegisterTransform


class TransformGenerator:
    def __init__(self, template: pwsAnalysis.PWSAnalysisResults, fastMode: bool = False, debugMode: bool = False):
        self._matcherFunc = ORBRegisterTransform if fastMode else SIFTRegisterTransform
        self._debugMode = debugMode
        self._template = template
        self._debugAnimationRef = None  # Just used to keep the animation alive.

    def match(self, ims: typing.Iterable[pwsAnalysis.PWSAnalysisResults]) -> typing.Iterable[np.ndarray]:
        logger = logging.getLogger(__name__)
        matchTime = time.time()
        logger.debug("Start match.")
        trans, self._debugAnimationRef = self._matcherFunc(self._template.meanReflectance, [im.meanReflectance for im in ims], debugPlots=self._debugMode)
        logger.debug(f"Matching took {time.time() - matchTime} seconds")
        return trans