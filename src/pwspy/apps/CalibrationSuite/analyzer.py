# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 16:44:06 2020

@author: nick
"""
import traceback
from datetime import datetime

import cv2

from pwspy.apps.CalibrationSuite.ITOMeasurement import ITOMeasurement
from pwspy.apps.CalibrationSuite.TransformGenerator import TransformGenerator
from pwspy.utility.reflection import Material
import pwspy.analysis.pws as pwsAnalysis
import numpy as np
import glob
import os


settings = pwsAnalysis.PWSAnalysisSettings.loadDefaultSettings("Recommended")
settings.referenceMaterial = Material.Air

class ITOAnalyzer:
    _SETTINGS = settings
    _DATETIMEFORMAT = "%m_%d_%Y"

    def __init__(self, directory: str, templateDirectory: str):
        self._template = ITOMeasurement(templateDirectory, self._SETTINGS)

        _measurements = []
        for f in glob(os.path.join(directory, '*')):
            if os.path.isdir(f):
                try:
                    _measurements.append(ITOMeasurement(f, self._SETTINGS))
                except Exception as e:
                    print(f"Failed to load measurement at directory {f}")
                    print(traceback.print_exc())

        self._matcher = TransformGenerator(self._template.analysisResults)

        dates = [datetime.strptime(i.name, self._DATETIMEFORMAT) for i in _measurements]
        self._data = pd.DataFrame({"measurements": _measurements}, index=dates)

        self._generateTransforms()

    def _generateTransforms(self, useCached: bool = True):
        # TODO how to cache transforms (Save to measurement directory with a reference to the template directory?)
        transforms = self._matcher.match(self._data.measurements)
        self._data['transforms'] = transforms

    def transformData(self):
        def applyTransform(row):
            tform = row.transforms
            #TODO determine how much the images will overlap and crop by that amount.
            im = row.measurements.results.meanReflectance
            tform = cv2.invertAffineTransform(row.transforms)
            meanReflectance = cv2.warpAffine(im, tform, im.shape)
            data = row.measurements.results.reflectance
            reflectance = np.zeros_like(data)
            for i in range(data.shape[2]):
                reflectance[:, :, i] = cv2.warpAffine(data[:, :, i], tform, data.shape[:2])

            return meanReflectance, reflectance

        out = self._data.apply(applyTransform, axis=1)
        a = 1

    #TODO measure average spectrum over a fine grid of the transformed image.