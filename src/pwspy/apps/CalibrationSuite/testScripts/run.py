# -*- coding: utf-8 -*-
"""
Created on Thu Dec 10 17:08:42 2020

@author: backman05
"""
from pwspy.apps.CalibrationSuite.TransformGenerator import TransformGenerator
from pwspy.apps.CalibrationSuite.analyzer import Analyzer, TransformedDataSaver, TransformedDataScorer
from pwspy.apps.CalibrationSuite.loaders import AbstractMeasurementLoader
import pwspy.dataTypes as pwsdt
from pwspy.apps.CalibrationSuite.ITOMeasurement import ITOMeasurement
from glob import glob
import pwspy.analysis.pws as pwsAnalysis
import os
import typing
from importlib import reload
import logging
reload(logging)  # This prevents the sys.stdout handler from being added mlutiple times when we re-run the script in spyder.
import sys


class Loader(AbstractMeasurementLoader):
    """
    An ITO calibration loader for this experiment. The reference for each ITO acquisiton is Cell3 from the same experiemental condition

    """
    analysisSettings = pwsAnalysis.PWSAnalysisSettings.loadDefaultSettings("Recommended")

    def __init__(self, rootDir: str, measurementSetName: str):
        meas = self.generateITOMeasurements(rootDir, measurementSetName)
        template = [m for m in meas if m.name == 'centered_0_52'][0]
        self._template = template
        self._measurements = meas

    @classmethod
    def generateITOMeasurements(cls, rootDir: str, measurementSetName: str):
        measurements = []
        for expType in ['centered', 'fieldstop', 'translation']:
            for condition in os.listdir(os.path.join(rootDir, expType)):
                if os.path.isdir(os.path.join(rootDir, expType, condition)):
                    itoAcq = pwsdt.AcqDir(os.path.join(rootDir, expType, condition, 'ito', 'Cell1'))
                    refAcq = pwsdt.AcqDir(os.path.join(rootDir, expType, condition, 'cells', "Cell3"))
                    name = f"{expType}_{condition}"
                    homeDir = os.path.join(rootDir, "calibrationResults", measurementSetName, name)
                    measurements.append(ITOMeasurement(homeDir, itoAcq, refAcq, cls.analysisSettings, name))
        return measurements

    @property
    def template(self) -> ITOMeasurement:
        return self._template

    @property
    def measurements(self) -> typing.Iterable[ITOMeasurement]:
        return tuple(self._measurements)


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
    transformer = TransformedDataSaver(loader, useCached=True, debugMode=True, method=TransformGenerator.Method.XCORR)
    for blur in list(range(1, 20)) + [None]:
        print(f"Starting blur {blur}")
        scorer = TransformedDataScorer(loader, str(blur), debugMode=True, blurSigma=blur)
    a = 1  # BreakPoint
