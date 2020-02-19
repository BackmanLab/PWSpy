from typing import List
import numpy as np
from pwspy.dataTypes import Roi, AcqDir
import matplotlib.pyplot as plt

def roiColor(data, rois: List[Roi], cmin, cmax, scale_bg, nuc_power_scale=1, scale_bar_nmperpixel=0):


    mask = np.zeros(rois[0].mask.shape, dtype=np.bool)
    for roi in rois:
        mask = np.logical_or(mask, roi.mask)

    # scale and process rms cube (this is probably not the best way to do it)
    data = data - cmin
    data[data < 0] = 0
    data[data > (cmax - cmin)] = cmax - cmin
    data = data**nuc_power_scale
    data = data * 1 / ((cmax - cmin)**nuc_power_scale) # normalize image so maximum value is 1

    # make the nucs red and everything else gray scale
    out = np.ones((data.shape[0], data.shape[1], 3)) * data[:, :, None] * scale_bg
    out[mask] = 0
    out[:,:,0] = out[:,:,0] + (mask * data)

    if (scale_bar_nmperpixel > 0):
        out[round(out.shape[0]*.965):round(out.shape[0]*.975), round(out.shape[0]*.03):round(out.shape[0]*.03+scale_bar_nmperpixel), :] = 1

    fig, ax = plt.subplots()
    ax.xaxis.set_visible(False)
    ax.imshow(out)
    fig.show()

if __name__ == "__main__":
    acq = AcqDir(r'G:\Aya_NAstudy\matchedNAi_largeNAc\cells\Cell2')
    an = acq.pws.loadAnalysis('p0')
    rois = [acq.loadRoi(name, num) for name, num, fformat in acq.getRois() if name=='nucleus']
    roiColor(an.rms, rois, 0, 1, 1, scale_bar_nmperpixel=100)
    a = 1