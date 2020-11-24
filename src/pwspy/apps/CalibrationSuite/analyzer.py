# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 16:44:06 2020

@author: nick
"""
import traceback
import typing
from datetime import datetime
import cv2
from pwspy.apps.CalibrationSuite.ITOMeasurement import ITOMeasurement
from pwspy.apps.CalibrationSuite.TransformGenerator import TransformGenerator
from pwspy.utility.reflection import Material
import pwspy.analysis.pws as pwsAnalysis
import numpy as np
from glob import glob
import os
import pandas as pd
import logging
from scipy.ndimage import binary_dilation
from scipy.signal import correlate
import weakref
settings = pwsAnalysis.PWSAnalysisSettings.loadDefaultSettings("Recommended")
settings.referenceMaterial = Material.Air


class ITOAnalyzer:
    _SETTINGS = settings
    _DATETIMEFORMAT = "%m_%d_%Y"

    def __init__(self, directory: str, templateDirectory: str):
        self._template = ITOMeasurement(templateDirectory, self._SETTINGS)

        self._measurements = []
        for f in glob(os.path.join(directory, '*')):
            if os.path.isdir(f):
                try:
                    self._measurements.append(ITOMeasurement(f, self._SETTINGS))
                except Exception as e:
                    print(f"Failed to load measurement at directory {f}")
                    print(traceback.print_exc())

        self._matcher = TransformGenerator(self._template.analysisResults, debugMode=False, fastMode=True)

        dates = [datetime.strptime(i.name, self._DATETIMEFORMAT) for i in self._measurements]
        self._data = pd.DataFrame({"measurements": [weakref.ref(i) for i in self._measurements]}, index=dates)

        #TODO use calibration results to save/load cached results
        self._generateTransforms()
        self.transformData()

    def _generateTransforms(self, useCached: bool = True):
        # TODO how to cache transforms (Save to measurement directory with a reference to the template directory?)
        transforms = self._matcher.match([i().analysisResults for i in self._data.measurements])
        self._data['transforms'] = transforms

    def transformData(self):
        logger = logging.getLogger(__name__)

        def applyTransform(row):
            if row.transforms is None:
                logger.debug(f"Skipping transformation of {row.measurements().name}")
                return None, None
            logger.debug(f"Starting data transformation of {row.measurements().name}")
            # TODO default warp interpolation is bilinear, should we instead use nearest-neighbor?
            im = row.measurements().analysisResults.meanReflectance
            tform = cv2.invertAffineTransform(row.transforms)
            meanReflectance = cv2.warpAffine(im, tform, im.shape, borderValue=-666.0)  # Blank regions after transform will have value -666, can be used to generate a mask.
            mask = meanReflectance == -666.0
            mask = binary_dilation(mask)  # Due to interpolation we sometimes get weird values at the edge. dilate the mask so that those edges get cut off.
            kcube = row.measurements().analysisResults.reflectance
            reflectance = np.zeros_like(kcube.data)
            for i in range(kcube.data.shape[2]):
                reflectance[:, :, i] = cv2.warpAffine(kcube.data[:, :, i], tform, kcube.data.shape[:2]) + meanReflectance
            row.measurements().analysisResults.releaseMemory()
            reflectance[mask] = np.nan
            return tuple((reflectance,))  # Bad things happen if you put a numpy array directly into a dataframe. That's why we have the tuple.

        self._data['reflectance'] = self._data.apply(applyTransform, axis=1)


class CubeComparer:
    """
    Compares the 3d reflectance cube of the template with the reflectance cube of a test measurement.
    The test reflectance array should have already been transformed so that they are aligned.
    Any blank section of the transformed test array should be `numpy.nan`

    Args:
        template: A 3d array of reflectance data that the test array will be compared against
        test: A 3d array to compare agains the template array. Since it is likely that the original data will need to have been transformed
            in order to align with the template there will blank regions. The pixels in the blank regions should be set to a value of `numpy.nan`
    """
    def __init__(self, template: np.ndarray, test: np.ndarray):
        assert isinstance(template, np.ndarray)
        assert isinstance(test, np.ndarray)
        self._template = template
        self._test = test

    def getCrossCorrelation(self):
        corr = correlate(self._template, self._test)  #Need to crop the nan regions
        return corr
    # TODO measure average spectrum over a fine grid of the transformed image.
    # TODO calculate 3d cross correlation function and measure slope in various directions.
    # TODO SSIM, MSE


class CubeSplitter:
    """
    Progressively splits a large cube into smaller and smaller cubes in the xy plane and performs an operation on the smaller cube sections.

    Args:
        arr: The original array we want to work with, May be 2 or 3 dimensional.
    """
    def __init__(self, arr: np.ndarray):
        assert (len(arr.shape) == 2) or (len(arr.shape) == 3)
        self._arr = arr

    def subdivide(self, factor: int) -> typing.List[typing.List[np.ndarray]]:
        """
        Split the array into a list of lists of sub arrays. The remainder pixels that can't be divided up equally are left out.

        Args:
            factor: The number to split each axis of the array by. For example, if `factor` is 2 then the array will be split into 4 arrays with sides that are half as long as the original.

        Returns:
            A list of lists of subdivided arrays from the original array.
        """
        shp = self._arr.shape
        divSize = (shp[0] // factor, shp[1] // factor)
        lst = []
        for i in range(factor):
            subLst = []
            for j in range(factor):
                slc = (slice(divSize[0]*i, divSize[0]*(i+1)), slice(divSize[1]*j, divSize[1]*(j+1)))
                subArr = self._arr[slc]
                subLst.append(subArr)
            lst.append(subLst)
        return lst
