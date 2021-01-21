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

"""Backing functions used by the activeContour script."""
import typing
import numpy as np
from skimage import morphology, segmentation
import matplotlib.pyplot as plt
import scipy.ndimage as ndi

# Convert snake to height map
def volume3Dto2D(arr3d, valueIndex=None, fillValue=0):
    """Convert a 3d boolean volume to a 2d array with values giving the height of the volume"""
    if valueIndex is None:
        valueIndex = np.arange(arr3d.shape[2])
    height = valueIndex[::-1][np.argmax(arr3d[:, :, ::-1], axis=2)]  # Get opdIndex value corresponding to highest True value in 3d array.
    height[~np.any(arr3d, axis=2)] = fillValue  # The above step doesn't work if no True values are found. Set pixels that are completely False to 0.
    return height


def equalAxis3dPlot(X: typing.Sequence[float], Y: typing.Sequence[float], Z: typing.Sequence[float], ax: plt.Axes):
    """With no built-in way to set the aspect of a 3d plot we force it with this. This function finds the bounding box
    of X, Y, and Z and then sets the limits of `ax` accordingly.

    Args:
        X: Sequence of x coordinates of data
        Y: Sequence of y coordinates of data
        Z: Sequence of z coordinates of data
        ax: The `Axes` that will be plotted to.

    """
    # Create cubic bounding box to simulate equal aspect ratio
    max_range = np.array([X.max() - X.min(), Y.max() - Y.min(), Z.max() - Z.min()]).max()
    Xb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][0].flatten() + 0.5 * (X.max() + X.min())
    Yb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][1].flatten() + 0.5 * (Y.max() + Y.min())
    Zb = 0.5 * max_range * np.mgrid[-1:2:2, -1:2:2, -1:2:2][2].flatten() + 0.5 * (Z.max() + Z.min())
    # Comment or uncomment following both lines to test the fake bounding box:
    for xb, yb, zb in zip(Xb, Yb, Zb):
        ax.plot([xb], [yb], [zb], 'w')


def morphSmoothing3D(arr: np.ndarray, radius: int):
    """Smooth a 3d boolean array along all 3 axes. Warning this is way too slow for radius > 10."""
    b = morphology.ball(radius)  # A 3d sphere structuring element.
    # #So Slow
    # arr = morphology.closing(arr, b)
    # arr = morphology.opening(arr, b)
    arr = ndi.binary_closing(arr, b)
    arr = ndi.binary_opening(arr, b)
    return arr


def morphSmoothing2D(arr: np.ndarray, radius: int):
    """Smooth a 3d boolean array only along the first and second axes. Warning this is way too slow for radius > 10."""
    b = morphology.disk(radius)  # A 3d sphere structuring element.
    arr = morphology.binary_closing(arr, b[:, :, None])
    arr = morphology.binary_opening(arr, b[:, :, None])
    return arr


def terminableSnake(arr: np.ndarray, smoothing=1, lambda1=1, lambda2=1, init_level_set='checkerboard'):
    """The morphological_chan_vese algorithm in scikit-image runs for a fixed number of iterations with no detection of when the process should terminate.
    This function attempts to detect when the algorithm is done and then forces it to terminate. Check the scikit-image documentation for a description
    of the input arguments and return values."""

    class EndItException(Exception):
        """We throw this exception to prematurely exit out of scikit-image's morphological_chan_vese algorithm."""
        pass

    def saveEvolution() -> typing.Tuple[typing.Callable, list, list]:
        """Generates a callback function  which is passed as `iter_callback` of the morphological_chan_vese algorithm.

        Returns: A tuple containing:
            A function to be passed as `iter_callback` to the morpholocial_chan_vese algorithm. It will throw an `EnditException`
            end the algorithm when it has determined that the algorithm has converged on a solution.

            A list containing the result of the algorithm after each iteration. Used to investigate the progress of the algorithm.

            A list containing the number of pixels that changed from false to true during each iteration. This is used to determine when a solution has started
            converging.
        """
        lst = []
        changes = []
        iteration = [0] # Just used to store an integer of how many times the function has been run.

        def _store(x: np.ndarray): # This function gets run at the end of each algorithm iteration. `x` is the current segmentation result.
            print(f'iter {iteration[0]}')  # Print out the iterationso we can view how fast we are proceeding.
            iteration[0] += 1
            if iteration[0] > 1:
                change = (x - lst[-1]).sum() / x.size  # calculate the ratio of pixels that have changed. note: this is signed, so if 10 pixel go from True to False and 10 pixels go from False to True we end up with 0.
                if len(changes) > 0:
                    if change * changes[-1] < 0: #If the sign of change has switched then we've gone from the segmentation growing to shrinking or vice-versa. The algorithm will alternate back and forth here, We use this as an indicator that the algorithm can be terminated.
                        lst.append(np.copy(x))  # Make sure to save our most recent result before exiting.
                        raise EndItException("Sign change")
                changes.append(change) # Store the change from this iteration to the last.
            lst.append(np.copy(x))

        return _store, lst, changes

    try:
        cb, l, changes = saveEvolution()
        snake = segmentation.morphological_chan_vese(arr, 100, smoothing=smoothing, lambda1=lambda1, lambda2=lambda2, iter_callback=cb,
                                                     init_level_set=init_level_set)
    except EndItException as e:
        print(e)
        snake = l[-1]
    return snake


def termSeg(arr: np.ndarray, smoothing=1, lambda1=1, lambda2=1, init_level_set='checkerboard'):
    """Start with a downscaled image and then move back up to full resoltuion to much more quickly segment an image.
    Check the scikit-image documentation for a description of the input arguments and return values."""
    from skimage.transform import downscale_local_mean, rescale

    if isinstance(init_level_set, np.ndarray):
        init_level_set = downscale_local_mean(init_level_set, (8, 8, 1)).astype(bool)

    img = downscale_local_mean(arr, (8, 8, 1))  # downscale by 8x in the x/y plane.
    snake = terminableSnake(img, smoothing, lambda1, lambda2, init_level_set)  # Segment the downscaled image.

    img = downscale_local_mean(arr, (2, 2, 1))  # downscale the original image by 2x in the x/y plane.
    snake = rescale(snake, (4, 4, 1), preserve_range=True, order=0).astype(bool)  # Upscale the previous segmentation result and use it as our starting point
    snake = terminableSnake(img, smoothing, lambda1, lambda2, snake) # Segment at 2x downscale.

    snake = rescale(snake, (2, 2, 1), preserve_range=True, order=0).astype(bool)  # Upscale the previous result to full resolution.
    snake = terminableSnake(arr, smoothing, lambda1, lambda2, snake)  # Use the previous result as a starting point for a final sementation at full resolution.

    return snake
