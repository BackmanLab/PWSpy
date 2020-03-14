import typing
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import animation


def calculateTransforms(reference: np.ndarray, other: typing.Iterable[np.ndarray], mask: np.ndarray = None, debugPlots: bool = False) -> typing.Iterable[np.ndarray]:
    """Given a 2D reference image and a list of other images of the same scene but shifted a bit this function will use OpenCV to calculate the transform from
    each of the other images to the reference. The transforms can be inverted using cv2.invertAffineTransform().
    It will return a list of transforms. Each transform is a 2x3 array in the form returned
    by opencv.estimateAffinePartial2d(). a boolean mask can be used to select which areas will be searched for features to be used
    in calculating the transform. This seems to work much better for normalized images.
    This code is basically a copy of this example, it can probably be improved upon:
    https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_feature2d/py_feature_homography/py_feature_homography.html"""
    import cv2
    def to8bit(arr: np.ndarray):
        Min = np.percentile(arr, 0.1)
        arr -= Min
        Max = np.percentile(arr, 99.9)
        arr = arr / Max * 255
        arr[arr < 0] = 0
        arr[arr > 255] = 255
        return arr.astype(np.uint8)

    refImg = to8bit(reference)
    MIN_MATCH_COUNT = 5
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
            plt.figure()
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