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
Useful functions for processing images. Currently its contents are focused
on image stabilization.

Functions
------------
.. autosummary::
   :toctree: generated/

   to8bit
   SIFTRegisterTransform
   ORBRegisterTransform
   edgeDetectRegisterTranslation

"""
from __future__ import annotations
import logging
import typing
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from skimage import feature
from skimage import registration
from mpl_qt_viz.visualizers import MultiPlot
if typing.TYPE_CHECKING:
    import cv2

logger = logging.getLogger(__name__)


def to8bit(arr: np.ndarray) -> np.ndarray:
    """Converts boolean or float type numpy arrays to 8bit and scales the data to span from 0 to 255. Used for many
    OpenCV functions.

    Args:
        arr: The input array

    Returns:
        The output array of dtype numpy.uint8
    """
    if arr.dtype == bool:
        arr = arr.astype(np.uint8) * 255
    else:
        arr = arr.astype(float) # This solves problems if the array is int16 type
        Min = np.percentile(arr, 0.1)
        arr -= Min
        Max = np.percentile(arr, 99.9)
        arr = arr / Max * 255
        arr[arr < 0] = 0
        arr[arr > 255] = 255
    return arr.astype(np.uint8)

def SIFTRegisterTransform(reference: np.ndarray, other: typing.Iterable[np.ndarray], mask: np.ndarray = None, debugPlots: bool = False) -> typing.Tuple[typing.List[np.ndarray], animation.ArtistAnimation]:
    """Given a 2D reference image and a list of other images of the same scene but shifted a bit this function will use OpenCV to calculate the transform from
    each of the other images to the reference. The transforms can be inverted using cv2.invertAffineTransform().
    It will return a list of transforms. Each transform is a 2x3 array in the form returned
    by opencv.estimateAffinePartial2d(). a boolean mask can be used to select which areas will be searched for features to be used
    in calculating the transform. This seems to work much better for normalized images.
    This code is basically a copy of this example, it can probably be improved upon:
    https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_feature2d/py_feature_homography/py_feature_homography.html

    Args:
        reference (np.ndarray): The 2d reference image.
        other (Iterable[np.ndarray]): An iterable containing the images that you want to calculate the translations for.
        mask (np.ndarray): A boolean array indicating which parts of the reference image should be analyzed. If `None` then the whole image will be used.
        debugPlots (bool): Indicates if extra plots should be openend showing the process of the function.

    Returns:
        tuple: A tuple containing:
            List[np.ndarray]:  Returns a list of transforms. Each transform is a 2x3 array in the form returned by opencv.estimateAffinePartial2d(). Note that even
            though they are returned as affine transforms they will only contain translation information, no scaling, shear, or rotation.

            ArtistAnimation: A reference the animation used to diplay the results of the function.
        """
    import cv2

    refImg = to8bit(reference)
    if mask:
        mask = mask.astype(np.uint8)

    #Set up flann matcher
    FLANN_INDEX_KDTREE = 0
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
    search_params = dict(checks=50)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    # Initiate SIFT detector
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(refImg, mask=mask)

    transforms = []
    if debugPlots:
        anFig, anAx = plt.subplots()
        anims = []
    for i, img in enumerate(other):
        logger.debug(f"Calculating SIFT matches for image {i} of {len(other)}")
        otherImg = to8bit(img)
        # find the keypoints and descriptors with SIFT
        kp2, des2 = sift.detectAndCompute(otherImg, mask=None)

        good = _knnMatch(flann, des1, des2)

        MIN_MATCH_COUNT = 5
        if len(good) > MIN_MATCH_COUNT:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, inlierMask = cv2.estimateAffinePartial2D(src_pts, dst_pts)
            matchesMask = inlierMask.ravel().tolist()
        else:
            logger.warning(f"Image {i}: Not enough matches are found - {len(good)}/{MIN_MATCH_COUNT}")
            M = None
            matchesMask = None
        transforms.append(M)
        if debugPlots and (M is not None):
            anims.append([anAx.imshow(cv2.warpAffine(otherImg, cv2.invertAffineTransform(M), otherImg.shape), 'gray')])
            h, w = refImg.shape
            pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
            dst = cv2.transform(pts, M)
            draw_params = dict(matchColor=(0, 255, 0),  # draw matches in green color
                               singlePointColor=None,
                               matchesMask=matchesMask,  # draw only inliers
                               flags=2)
            img2 = cv2.polylines(otherImg, [np.int32(dst)], True, 255, 3, cv2.LINE_AA)
            img3 = cv2.drawMatches(refImg, kp1, img2, kp2, good, None, **draw_params)
            fig, ax = plt.subplots()
            ax.imshow(img3, 'gray')
    if debugPlots:
        anFig.suptitle("SIFT: If transforms worked, image should not appear to move.")
        an = animation.ArtistAnimation(anFig, anims)
    else:
        an = None
    return transforms, an


def ORBRegisterTransform(reference: np.ndarray, other: typing.Iterable[np.ndarray], mask: np.ndarray = None, debugPlots: bool = False) -> typing.Tuple[typing.List[np.ndarray], animation.ArtistAnimation]:
    """Given a 2D reference image and a list of other images of the same scene but shifted a bit this function will use OpenCV to calculate the transform from
    each of the other images to the reference. The transforms can be inverted using cv2.invertAffineTransform().
    It will return a list of transforms. Each transform is a 2x3 array in the form returned
    by opencv.estimateAffinePartial2d(). a boolean mask can be used to select which areas will be searched for features to be used
    in calculating the transform. 

    Args:
        reference (np.ndarray): The 2d reference image.
        other (Iterable[np.ndarray]): An iterable containing the images that you want to calculate the translations for.
        mask (np.ndarray): A boolean array indicating which parts of the reference image should be analyzed. If `None` then the whole image will be used.
        debugPlots (bool): Indicates if extra plots should be openend showing the process of the function.

    Returns:
        tuple: A tuple containing:
            List[np.ndarray]:  Returns a list of transforms. Each transform is a 2x3 array in the form returned by opencv.estimateAffinePartial2d(). Note that even
            though they are returned as affine transforms they will only contain translation information, no scaling, shear, or rotation.

            ArtistAnimation: A reference the animation used to diplay the results of the function.
        """
    import cv2

    refImg = to8bit(reference)
    if mask:
        mask = mask.astype(np.uint8)

    #Create FLANN matcher
    FLANN_INDEX_LSH = 6
    index_params = dict(algorithm=FLANN_INDEX_LSH,
                        table_number=6,  # 12
                        key_size=12,  # 20
                        multi_probe_level=1)  # 2
    search_params = dict(checks=100)
    flann = cv2.FlannBasedMatcher(index_params, search_params)

    # Initiate ORB detector
    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(refImg, mask=mask)

    transforms = []
    if debugPlots:
        anFig, anAx = plt.subplots()
        anims = []
    for i, img in enumerate(other):
        otherImg = to8bit(img)
        # find the keypoints and descriptors with ORB
        kp2, des2 = orb.detectAndCompute(otherImg, mask=None)

        good = _knnMatch(flann, des1, des2)

        MIN_MATCH_COUNT = 5
        if len(good) > MIN_MATCH_COUNT:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, inlierMask = cv2.estimateAffinePartial2D(src_pts, dst_pts)
            matchesMask = inlierMask.ravel().tolist()
        else:
            logging.getLogger(__name__).warning(f"Image {i}: Not enough matches are found - {len(good)}/{MIN_MATCH_COUNT}")
            M = None
            matchesMask = None
        transforms.append(M)
        if debugPlots and (M is not None):
            anims.append([anAx.imshow(cv2.warpAffine(otherImg, cv2.invertAffineTransform(M), otherImg.shape), 'gray')])
            h, w = refImg.shape
            pts = np.float32([[0, 0], [0, h - 1], [w - 1, h - 1], [w - 1, 0]]).reshape(-1, 1, 2)
            dst = cv2.transform(pts, M)
            draw_params = dict(matchColor=(0, 255, 0),  # draw matches in green color
                               singlePointColor=None,
                               matchesMask=matchesMask,  # draw only inliers
                               flags=2)
            img2 = cv2.polylines(otherImg, [np.int32(dst)], True, 255, 3, cv2.LINE_AA)
            img3 = cv2.drawMatches(refImg, kp1, img2, kp2, good, None, **draw_params)
            fig, ax = plt.subplots()
            ax.imshow(img3, 'gray')
    if debugPlots:
        anFig.suptitle("ORB: If transforms worked, image should not appear to move.")
        an = animation.ArtistAnimation(anFig, anims)
    else:
        an = None
    return transforms, an


def _knnMatch(flannMatcher: cv2.FlannBasedMatcher, des1: np.ndarray, des2: np.ndarray) -> typing.List[cv2.DMatch]:
    """
    Return a list of sufficiently good matches between keypoint descriptors.

    Args:
        flannMatcher: The opencv FLANN matcher object
        des1: An array of `query descriptors` to find matches for.
        des2: An array of `train descriptors` to check as matches for des1
    Returns:
        A list of the selecte opencv DMatch objects
    """
    matches = flannMatcher.knnMatch(des1, des2, k=2)  # Return the two best matches. Note, might only return 1 match
    # store all the good matches as per Lowe's ratio test.
    good = []
    for iMatches in matches:
        if len(iMatches) == 1:
            good.append(iMatches[0])  # If only one match was found keep it
        elif len(iMatches) == 2:
            if iMatches[0].distance < 0.7 * iMatches[1].distance:  # This is known as Lowe's Ratio Test. If two matches were returned only keep the best match if it is sufficiently better than the second best match
                good.append(iMatches[0])
        else:
            raise Exception("Programming Error!")
    return good

def edgeDetectRegisterTranslation(reference: np.ndarray, other: typing.Iterable[np.ndarray], mask: np.ndarray = None, debugPlots: bool = False, sigma: float = 3) -> typing.Tuple[typing.Iterable[np.ndarray], typing.List]:
    """This function is used to find the relative translation between a reference image and a list of other similar images. Unlike `SIFRegisterTransforms` this function
    will not work for images that are rotated relative to the reference. However, it does provide more robust performance for images that do not look identical.

    Args:
        reference (np.ndarray): The 2d reference image.
        other (Iterable[np.ndarray]): An iterable containing the images that you want to calculate the translations for.
        mask (np.ndarray): A boolean array indicating which parts of the reference image should be analyzed. If `None` then the whole image will be used.
        debugPlots (bool): Indicates if extra plots should be openend showing the process of the function.
        sigma (float): this parameter is passed to skimage.feature.canny to detect edges.

    Returns:
        tuple: A tuple containing:
            list[np.ndarray]:  Returns a list of transforms. Each transform is a 2x3 array in the form returned by opencv.estimateAffinePartial2d(). Note that even
            though they are returned as affine transforms they will only contain translation information, no scaling, shear, or rotation.

            list: A list of references to the plotting widgets used to display the results of the function.
    """
    import cv2
    refEd = feature.canny(reference, sigma=sigma)
    if mask is not None: refEd[~mask] = False  # Clear any detected edges outside of the mask
    imEd = [feature.canny(im, sigma=sigma) for im in other]
    affineTransforms = []
    if debugPlots:
        anEdFig, anEdAx = plt.subplots()
        anEdFig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        anEdAx.get_xaxis().set_visible(False)
        anEdAx.get_yaxis().set_visible(False)
        anFig, anAx = plt.subplots()
        anFig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        anAx.get_xaxis().set_visible(False)
        anAx.get_yaxis().set_visible(False)
        anims = [[anAx.imshow(to8bit(reference), 'gray'), anAx.text(100, 100, "Reference", color='r')]]
        animsEd = [[anEdAx.imshow(to8bit(refEd), 'gray'), anEdAx.text(100, 100, "Reference",  color='w')]]
    for i, (im, edgeIm) in enumerate(zip(other, imEd)):
        shifts, error, phasediff = feature.register_translation(edgeIm, refEd)
        logging.getLogger(__name__).info(f"Translation: {shifts}, RMS Error: {error}, Phase Difference:{phasediff}")
        shifts = np.array([[1, 0, shifts[1]],
                           [0, 1, shifts[0]]], dtype=float) # Convert the shift to an affine transform
        affineTransforms.append(shifts)
        if debugPlots:
            plt.figure()
            animsEd.append([anEdAx.imshow(cv2.warpAffine(to8bit(edgeIm), cv2.invertAffineTransform(shifts), edgeIm.shape), 'gray'),  anEdAx.text(100, 100, str(i),  color='w')])
            anims.append([anAx.imshow(cv2.warpAffine(to8bit(im), cv2.invertAffineTransform(shifts), im.shape), 'gray'),  anAx.text(100, 100, str(i), color='r')])
    if debugPlots:
        an = [MultiPlot(anims, "If transforms worked, cells should not appear to move."), MultiPlot(animsEd, "If transforms worked, cells should not appear to move.")]
        [i.show() for i in an]
    else:
        an = []
    return affineTransforms, an


def crossCorrelateRegisterTranslation(reference: np.ndarray, other: typing.Iterable[np.ndarray], debugPlots: bool = False) -> typing.Tuple[typing.Iterable[np.ndarray], MultiPlot]:
    """This function is used to find the relative translation between a reference image and a list of other similar images. Unlike `SIFRegisterTransforms` this function
    will not work for images that are rotated relative to the reference.

    Args:
        reference (np.ndarray): The 2d reference image.
        other (Iterable[np.ndarray]): An iterable containing the images that you want to calculate the translations for.
        debugPlots (bool): Indicates if extra plots should be openend showing the process of the function.

    Returns:
        tuple: A tuple containing:
            list[np.ndarray]:  Returns a list of transforms. Each transform is a 2x3 array in the form returned by opencv.estimateAffinePartial2d(). Note that even
                though they are returned as affine transforms they will only contain translation information, no scaling, shear, or rotation.

            MultiPlot: A reference to the plotting widgets used to display the results of the function. If `debugPlots` is False this will be `None`
    """
    import cv2
    if debugPlots:
        anFig, anAx = plt.subplots()
        anFig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        anAx.get_xaxis().set_visible(False)
        anAx.get_yaxis().set_visible(False)
        anims = [[anAx.imshow(to8bit(reference), 'gray'), anAx.text(100, 100, "Reference", color='r')]]
    affineTransforms = []
    for i, im in enumerate(other):
        shifts, error, phasediff = registration.phase_cross_correlation(im, reference, return_error=True)
        logging.getLogger(__name__).debug(f"Translation: {shifts}, RMS Error: {error}, Phase Difference:{phasediff}")
        shifts = np.array([[1, 0, shifts[1]],
                           [0, 1, shifts[0]]], dtype=float) # Convert the shift to an affine transform
        affineTransforms.append(shifts)
        if debugPlots:
            anims.append([
                anAx.imshow(cv2.warpAffine(to8bit(im), cv2.invertAffineTransform(shifts), im.shape), 'gray'),
                anAx.text(100, 100, str(i), color='r')])
    if debugPlots:
        an = MultiPlot(anims, "If transforms worked, images should not appear to move.")
        an.show()
    else:
        an = None
    return affineTransforms, an
