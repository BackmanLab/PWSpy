# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

"""
Functions for segmenting out fluorescent regions of an image.

Functions
-----------
.. autosummary::
   :toctree: generated/

   segmentOtsu
   segmentAdaptive
   segmentWatershed
   updateFolderStructure

"""

import os
import typing
from glob import glob
from typing import List
from skimage import morphology, measure, segmentation
import cv2
import numpy as np
import shapely
import tifffile as tf
from shapely.geometry import MultiPolygon
import pwspy.dataTypes as pwsdt
import scipy.ndimage as ndim

from pwspy.utility import machineVision


def segmentOtsu(image: np.ndarray, minArea=100) -> List[shapely.geometry.Polygon]:
    """Uses non-adaptive otsu method segmentation to find fluorescent regions (nuclei)
    Returns a list of shapely polygons.

    Args:
        image:  a 2d array representing the fluorescent image.
        minArea: Detected regions with a pixel area lower than this value will be discarded.

    Returns:
        A list of `shapely.geometry.Polygon` objects corresponding to detected nuclei.
    """
    image = machineVision.to8bit(image)  # convert to 8bit
    threshold, binary = cv2.threshold(image, 0, 1, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    polys = _binaryToPoly(binary)
    newPolys = []
    for p in polys:
        newPolys += _processPoly(p, erode=0, dilate=0, polySimplification=2, minArea=minArea)
    return newPolys


def _binaryToPoly(binary: np.ndarray) -> typing.List[shapely.geometry.Polygon]:
    binary = machineVision.to8bit(binary)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polys = []
    for contour in contours:
        contour = contour.squeeze()  # We want a Nx2 array. We get Nx1x2 though.
        if len(contour.shape) != 2:  # Sometimes contour is 1x1x2 which squezes down to just 2
            continue
        if contour.shape[0] < 3:  # We need a polygon, not a line
            continue
        p = shapely.geometry.Polygon(contour)
        polys.append(p)
    return polys


def _processPoly(p: shapely.geometry.Polygon, erode: int = 0, dilate: int = 0, polySimplification: int = 5, minArea: int = 100):
    if erode != 0:
        p = p.buffer(-erode)
    if not isinstance(p, MultiPolygon):  # there is a chance for this to split a polygon into a multipolygon. we iterate over each new polygon. If it's still just a polygon put it in a list so it can be iterated over wit the same syntax
        p = [p]
    polys = []
    for poly in p:
        if dilate != 0:
            poly = poly.buffer(dilate)  # This is an erode followed by a dilate.
        poly = poly.simplify(polySimplification, preserve_topology=False)  # This removed unneed points to lessen the saving/loading burden
        if poly.area < minArea:
            continue
        polys.append(poly)
    return polys


def segmentAdaptive(image: np.ndarray, minArea: int = 100, adaptiveRange: int = 500, thresholdOffset: float = -10,
                    polySimplification: int = 5, dilate: int = 0, erode: int = 0) -> List[shapely.geometry.Polygon]:
    """Uses opencv's `cv2.adaptiveThreshold` function to segment nuclei in a fluorescence image.

    Args:
        image: A 2d array representing the fluorescent image.
        minArea: Detected regions with a pixel area lower than this value will be discarded.
        adaptiveRange: Adjusts the range of the segmentation threshold adapts
        thresholdOffset: This offset is passed to `cv2.adaptiveThreshold` and affects the segmentation process
        polySimplification: This parameter will simplify the edges of the detected polygons to remove overly complicated
            geometry
        dilate: The number of pixels that the polygons should be dilated by.
        erode: The number of pixels that the polygons should be eroded by. Combining this with dilation can help to
            close gaps.

    Returns:
        A list of `shapely.geometry.Polygon` objects corresponding to detected nuclei.
    """
    if adaptiveRange%2 != 1 or adaptiveRange<3:
        raise ValueError("adaptiveRange must be a positive odd integer >=3.")
    image = machineVision.to8bit(image)  # convert to 8bit
    binary = cv2.adaptiveThreshold(image, 1, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, adaptiveRange, thresholdOffset)
    polys = _binaryToPoly(binary)
    newPolys = []
    for i, p in enumerate(polys):
        newPolys += _processPoly(p, erode, dilate, polySimplification, minArea)
    return newPolys


def segmentWatershed(image: np.ndarray, closingRadius: int = 2, openingRadius: int = 2, minimumArea: int = 2000):
    """
    Use watershed with otsu thresholding to segment bright sections of an image. Does a good job of keeping adaject nuclei separate.

    Args:
        image: a 2d numpy array containing image intensity information.
        closingRadius: The kernel radius to be used for a binary closing operation that eliminated small empty regions of the segmentation mask
        openingRadius: The kernel radius to be used for a binary opening operation that eliminated small filled regions of the segmentation mask
        minimumArea: Polygons below this area (in pixels) will not be returned.
    """
    image = machineVision.to8bit(image)
    threshold, binary = cv2.threshold(image, 0, 1, cv2.THRESH_BINARY | cv2.THRESH_OTSU) # TODO switch to adaptive?
    binary = morphology.binary_opening(binary, morphology.disk(openingRadius))
    binary = morphology.binary_closing(binary,  morphology.disk(closingRadius))

    # Remove objects smaller than 2000 pixels
    labeled = measure.label(binary)
    props = measure.regionprops(labeled)
    for regionProp in props:
        if regionProp.area < minimumArea:
            binary[labeled == regionProp.label] = 0
    # Invert the mask and compute the Euclidean distance
    # transform
    disttrans = -ndim.distance_transform_edt(binary)  # The distance from the edge of the segmented nuclei.
    hmin = morphology.extrema.h_minima(disttrans, 20)  # Should be a tiny true region at the center of each nuclei

    d = disttrans.astype(int)
    d = d - d.min()
    ws = segmentation.watershed(d, markers=measure.label(hmin), mask=binary)
    # ws = segmentation.clear_border(ws)  # Clear incomplete nuclei on the border.
    polys = _binaryToPoly(ws)
    return polys


def updateFolderStructure(rootDirectory: str, rotate: int, flipX: bool, flipY: bool):
    """Used to translate old fluorescence images to the new file organization that is recognized by the code.

    Args:
        rootDirectory: The top level directory containing fluorescence images that were saved in the old `FL_Cell{X}` folder format
        rotate: The number of times that the images should be rotated clockwise to match up with the PWS images they go with
        flipX: Should the images be mirrored over the X-axis after being rotated?
        flipY: Should the images be mirrored over the Y-axis after being rotated?

    """

    files = glob(os.path.join(rootDirectory, '**', 'FL_Cell*'), recursive=True)
    for file in files:
        cellNum = int(file.split('FL_Cell')[-1])
        parentPath = file.split("FL_Cell")[0]
        data = tf.imread(os.path.join(file, 'image_bd.tif'))
        data = np.rot90(data, k=rotate)
        if flipX:
            data = np.flip(data, axis=1)
        if flipY:
            data = np.flip(data, axis=0)
        fl = pwsdt.FluorescenceImage(data, {'exposure': None})
        newPath = os.path.join(parentPath, f'Cell{cellNum}', 'Fluorescence')
        os.mkdir(newPath)
        fl.toTiff(newPath)

if __name__ == '__main__':
    fl = pwsdt.FluorescenceImage.fromTiff(r'G:\Data\canvassing\testcells\Cell1904\Fluorescence')
    segmentWatershed(fl.data)