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

def segmentAdaptive(image: np.ndarray, minArea = 100, adaptiveRange: int = 21, subtract: float=13, polySimplification: int = 2) -> shapely.geometry.Polygon:
    """Uses opencv's adaptive"""
    if adaptiveRange%2 != 1 or adaptiveRange<3:
        raise ValueError("adaptiveRange must be a positive odd integer >=3.")
    image = ((image - image.min()) / (image.max() - image.min()) * 255).astype(np.uint8) # convert to 8bit
    binary = cv2.adaptiveThreshold(image, 1, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, adaptiveRange, subtract)
    contImage, contours, hierarchy = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    polys = []
    for contour in contours:
        contour = contour.squeeze()  # We want a Nx2 array. We get Nx1x2 though.
        if len(contour.shape) != 2:  # Sometimes contour is 1x1x2 which squezes down to just 2
            continue
        if contour.shape[0] < 3:  # We need a polygon, not a line
            continue
        p = shapely.geometry.Polygon(contour)
        if polySimplification != 0:
            p = p.buffer(-polySimplification).buffer(polySimplification) #This is an erode followed by a dilate.
        p = p.simplify(polySimplification, preserve_topology=False) #This removed unneed points to lessen the saving loading burden
        if isinstance(p, MultiPolygon):  # There is a chance for this to convert a Polygon to a Multipolygon.
            p = max(p, key=lambda a: a.area)  # To fix this we extract the largest polygon from the multipolygon
        if p.area < minArea:  # Reject small regions
            continue
        polys.append(p)
    return polys