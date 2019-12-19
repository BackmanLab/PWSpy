from typing import List

import numpy as np
import cv2
import shapely
from shapely.geometry import MultiPolygon


def segmentOtsu(image: np.ndarray, minArea = 100):
    """Uses non-adaptive otsu method segmentation to find fluorescent regions (nuclei)
    Returns a list of shapely polygons."""
    image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8)
    threshold, binary = cv2.threshold(image, 0, 1, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    contImage, contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
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

def segmentAdaptive(image: np.ndarray, minArea = 100, adaptiveRange: int = 500, thresholdOffset: float=-10, polySimplification: int = 5, dilate: int = 0, erode: int = 0) -> List[shapely.geometry.Polygon]:
    """Uses opencv's adaptive"""
    if adaptiveRange%2 != 1 or adaptiveRange<3:
        raise ValueError("adaptiveRange must be a positive odd integer >=3.")
    image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8) # convert to 8bit
    binary = cv2.adaptiveThreshold(image, 1, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, adaptiveRange, thresholdOffset)
    contImage, contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
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