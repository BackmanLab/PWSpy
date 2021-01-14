# -*- coding: utf-8 -*-
"""
Created on Thu Dec 10 17:08:42 2020

@author: backman05
"""
from pwspy.apps.CalibrationSuite.TransformGenerator import TransformGenerator
from pwspy.apps.CalibrationSuite.analyzer import Analyzer, TransformedDataSaver, TransformedDataScorer
from loader import Loader
from importlib import reload
import logging
reload(logging)  # This prevents the sys.stdout handler from being added mlutiple times when we re-run the script in spyder.
import sys
import time


def configureLogger():
    logger = logging.getLogger()  # We get the root logger so that all loggers in pwspy will be handled.
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-4s %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


if __name__ == '__main__':
    import matplotlib.pyplot as plt
    import experimentInfo
    plt.ion()
    logger = configureLogger()
    measurementSet = 'xcorr_blurScan'
    loader = Loader(experimentInfo.workingDirectory, measurementSet)
    transformer = TransformedDataSaver(loader, useCached=True, debugMode=False, method=TransformGenerator.Method.XCORR)

    # CLear all existing scores.
    for m in loader.measurements:
        tData = m.loadTransformedData(loader.template.idTag)
        tData.clearScores()

    # Start scoring.
    for blur in list(range(1, 15)) + [None]:
        logger.info(f"Starting blur {blur}")
        stime = time.time()
        scorer = TransformedDataScorer(loader, str(blur), debugMode=False, blurSigma=blur,
                                       parallel=False)
        logger.info(f"Total score time: {time.time() - stime}")
    a = 1  # BreakPoint
