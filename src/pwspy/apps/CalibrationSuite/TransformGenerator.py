import time
import typing

import numpy as np

from pwspy.analysis import pws as pwsAnalysis
from pwspy.utility.machineVision import ORBRegisterTransform, SIFTRegisterTransform


class TransformGenerator:
    def __init__(self, template: pwsAnalysis.PWSAnalysisResults, fastMode: bool = False, debugMode: bool = False):
        self._matcherFunc = ORBRegisterTransform if fastMode else SIFTRegisterTransform
        self._debugMode = debugMode
        self._template = template

    def match(self, ims: typing.Iterable[pwsAnalysis.PWSAnalysisResults]) -> typing.Iterable[np.ndarray]:
        if self._debugMode:
            matchTime = time.time()
            print("Start match.")
        trans, animation = self._matcherFunc(self._template.meanReflectance, [im.meanReflectance for im in ims], debugPlots=self._debugMode)
        if self._debugMode:
            print(f"Matching took {time.time() - matchTime} seconds")
        return trans