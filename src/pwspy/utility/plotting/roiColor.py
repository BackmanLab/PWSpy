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

from typing import List
import numpy as np
from pwspy.dataTypes import Roi, AcqDir
import matplotlib.pyplot as plt
import matplotlib


def roiColor(data, rois: List[Roi], vmin, vmax, scale_bg, hue=0, exponent=1, numScaleBarPix=0):
    """Given a 2D image of data this funciton will scale the data, apply an exponential curve, and color the ROI regions with Hue.
    Args:
        data (np.ndarray): an MxN array of data to be imaged
        rois (List[Roi]): a list of Roi objects. the regions inside a roi will be colored.
        vmin (float): the minimum value in the data that will be set to black
        vmax (float): the maximum value in the data that will be set to white
        scale_bg (float): Scales the brightness of the background (non-roi) region.
        hue (float): A value of 0-1 indicating the hue of the colored regions.
        exponent (float): The exponent used to curve the color map for more pleasing results.
        numScaleBarPix (float): The length of the scale bar in number of pixels.
    Returns:
        np.ndarray: MxNx3 RGB array of the image"""

    mask = np.zeros(rois[0].mask.shape, dtype=np.bool)
    for roi in rois:
        mask = np.logical_or(mask, roi.mask)

    # scale and process rms cube (this is probably not the best way to do it)
    data = data - vmin
    data[data < 0] = 0
    data[data > (vmax - vmin)] = vmax - vmin
    data = data ** exponent
    data = data * 1 / ((vmax - vmin) ** exponent) # normalize image so maximum value is 1

    # make the nucs red and everything else gray scale
    hsv = np.ones((data.shape[0], data.shape[1], 3))
    hsv[:,:,2] = data
    hsv[:,:,2][~mask] *= scale_bg
    hsv[:,:,0] = hue
    hsv[:,:,1][~mask] = 0
    out = matplotlib.colors.hsv_to_rgb(hsv)

    if (numScaleBarPix > 0):
        out[round(out.shape[0]*.965):round(out.shape[0]*.975), round(out.shape[0]*.03):round(out.shape[0] * .03 + numScaleBarPix), :] = 1

    return out

if __name__ == "__main__":
    acq = AcqDir(r'G:\Aya_NAstudy\matchedNAi_largeNAc\cells\Cell3')
    an = acq.pws.loadAnalysis('p0')
    rois = [acq.loadRoi(name, num) for name, num, fformat in acq.getRois() if name=='nucleus']
    out = roiColor(an.rms, rois, 0.04, .3, 1, exponent=1.1, numScaleBarPix=100)
    fig, ax = plt.subplots()
    ax.xaxis.set_visible(False)
    ax.yaxis.set_visible(False)
    ax.imshow(out)#, vmax=vmax, vmin=vmin)
    fig.show()
    a = 1