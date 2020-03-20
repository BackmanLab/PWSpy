import typing
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation
from skimage import feature
from skimage import morphology

from pwspy.utility.plotting._multiPlot import MultiPlot


def to8bit(arr: np.ndarray):
    if arr.dtype == bool:
        arr = arr.astype(np.uint8) * 255
    else:
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
    #TODO this function does some weird stuff in the case that MIN_MATTCH_COUNT is not met for some of the images due to variables not being defined.
    import cv2

    refImg = to8bit(reference)
    MIN_MATCH_COUNT = 10
    FLANN_INDEX_KDTREE = 0

    # Initiate SIFT detector
    sift = cv2.xfeatures2d.SIFT_create()  # By default this function is not included, you need a specially built version of Opencv due to patent issues :( Maybe try MOPS instead
    mask = mask.astype(np.uint8)
    kp1, des1 = sift.detectAndCompute(refImg, mask=mask)

    transforms = []
    anFig, anAx = plt.subplots()
    anims = []
    for img in other:
        otherImg = to8bit(img)
        # find the keypoints and descriptors with SIFT
        kp2, des2 = sift.detectAndCompute(otherImg, mask=mask)
        index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=5)
        search_params = dict(checks=50)
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)
        # store all the good matches as per Lowe's ratio test.
        good = []
        for m, n in matches:
            if m.distance < 0.7 * n.distance:
                good.append(m)
        if len(good) > MIN_MATCH_COUNT:
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            M, mask = cv2.estimateAffinePartial2D(src_pts, dst_pts)
            transforms.append(M)
            matchesMask = mask.ravel().tolist()
        else:
            print("Not enough matches are found - %d/%d" % (len(good), MIN_MATCH_COUNT))
            matchesMask = None
            # M = None
        if debugPlots:
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
            plt.imshow(img3, 'gray')
            plt.show()
    if debugPlots:
        anFig.suptitle("If transforms worked, cells should not appear to move.")
        an = animation.ArtistAnimation(anFig, anims)
    return transforms, an


def edgeDetectRegisterTranslation(reference: np.ndarray, other: typing.Iterable[np.ndarray], mask: np.ndarray = None, debugPlots: bool = False, sigma: float = 3) -> typing.Tuple[typing.Iterable[np.ndarray], typing.List]:
    """This function is used to find the relative translation between a reference image and a list of other similar images. Unlike `calculateTransforms` this function
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
        anEdAx.get_xaxis().set_visible(False)
        anEdAx.get_yaxis().set_visible(False)
        anFig, anAx = plt.subplots()
        anAx.get_xaxis().set_visible(False)
        anAx.get_yaxis().set_visible(False)
        anims = [[anAx.imshow(to8bit(reference), 'gray'), anAx.text(100, 100, "Reference", color='r')]]
        animsEd = [[anEdAx.imshow(to8bit(refEd), 'gray'), anEdAx.text(100, 100, "Reference",  color='w')]]
    for i, (im, edgeIm) in enumerate(zip(other, imEd)):
        shifts, error, phasediff = feature.register_translation(edgeIm, refEd)
        print(f"Translation: {shifts}, RMS Error: {error}, Phase Difference:{phasediff}")
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
