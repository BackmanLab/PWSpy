"""
==================================================
Fluorescence (:mod:`pwspy.utility.fluorescence`)
==================================================
This module provides a number of functions useful for
segmenting out fluorescent regions of an image.

Functions
-----------
.. autosummary::
   :toctree: generated/

   segmentOtsu
   segmentAdaptive
   updateFolderStructure

"""

import os
from glob import glob
from typing import List

import cv2
import numpy as np
import shapely
import tifffile as tf
from shapely.geometry import MultiPolygon
import pwspy.dataTypes as pwsdt

def segmentOtsu(image: np.ndarray, minArea = 100) -> List[shapely.geometry.Polygon]:
    """Uses non-adaptive otsu method segmentation to find fluorescent regions (nuclei)
    Returns a list of shapely polygons.

    Args:
        image:  a 2d array representing the fluorescent image.
        minArea: Detected regions with a pixel area lower than this value will be discarded.

    Returns:
        A list of `shapely.geometry.Polygon` objects corresponding to detected nuclei.
    """
    image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8)
    threshold, binary = cv2.threshold(image, 0, 1, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polys = []
    for contour in contours:
        contour = contour.squeeze()  # We want a Nx2 array. We get Nx1x2 though.
        if len(contour.shape) != 2:  # Sometimes contour is 1x1x2 which squezes down to just 2
            continue
        if contour.shape[0] < 3:  # We need a polygon, not a line
            continue
        p = shapely.geometry.Polygon(contour)
        if p.area < minArea:  # Reject small regions
            continue
        polys.append(p)
    return polys


def segmentAdaptive(image: np.ndarray, minArea: int = 100, adaptiveRange: int = 500, thresholdOffset: float = -10,
                    polySimplification: int = 5, dilate: int = 0, erode: int = 0) -> List[shapely.geometry.Polygon]:
    """Uses opencv's `cv2.adaptiveThreshold` function to segment nuclei in a fluorescence image.

    Args:
        image: A 2d array representing the fluorescent image.
        minArea: Detected regions with a pixel area lower than this value will be discarded.
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
    image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8) # convert to 8bit
    binary = cv2.adaptiveThreshold(image, 1, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, adaptiveRange, thresholdOffset)
    contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polys = []
    for contour in contours:
        contour = contour.squeeze()  # We want a Nx2 array. We get Nx1x2 though.
        if len(contour.shape) != 2:  # Sometimes contour is 1x1x2 which squezes down to just 2
            continue
        if contour.shape[0] < 3:  # We need a polygon, not a line
            continue
        p = shapely.geometry.Polygon(contour)
        p = p.buffer(-erode)
        if not isinstance(p, MultiPolygon): #there is a chance for this to split a polygon into a multipolygon. we iterate over each new polygon. If it's still just a polygon put it in a list so it can be iterated over wit the same syntax
            p = [p]
        for poly in p:
            poly = poly.buffer(dilate) #This is an erode followed by a dilate.
            poly = poly.simplify(polySimplification, preserve_topology=False) #This removed unneed points to lessen the saving/loading burden
            if poly.area < minArea:
                continue
            polys.append(poly)
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