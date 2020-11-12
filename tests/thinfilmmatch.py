# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 16:44:06 2020

@author: nick
"""
if __name__ == '__main__':
    from glob import glob
    import matplotlib.pyplot as plt
    from pwspy import dataTypes as pwsdt
    import pandas as pd
    import os
    from pwspy.utility.machineVision import SIFTRegisterTransform, ORBRegisterTransform
    import time

    fast = True  # Use ORB or SIFT. ORB is much faster but SIFT seems to find more keypoints and is more stable.
    refNum = 3  # The cell number to use as the `template`. other images will be compared to this one.

    plt.ion()
    wDir = r'\\backmanlabnas.myqnapcloud.com\AcquiredData\Nick\ITOPositionStability'
    files = glob(os.path.join(wDir, "Cell*"))
    acqs = [pwsdt.AcqDir(f) for f in files]

    nums = [int(acq.filePath.split("Cell")[-1]) for acq in acqs]

    df = pd.DataFrame({'acq': acqs, 'num': nums})
    df['thumb'] = df.apply(lambda row: row.acq.pws.getThumbnail(), axis=1)
    df = df.set_index(df.num)

    ref = df.loc[999].acq.pws.toDataClass()
    ref.correctCameraEffects()
    ref.normalizeByExposure()
    ref.filterDust(1)

    df = df.loc[[1, 2, 3, 4, 5]]


    def normalize(row):
        data: pwsdt.ImCube = row.acq.pws.toDataClass()
        data.correctCameraEffects()
        data.normalizeByExposure()
        data.normalizeByReference(ref)
        return data

    # Normalizing data
    print("Normalizing Data")
    df['data'] = df.apply(normalize, axis=1)
    del ref

    refRow = df.loc[refNum]
    df = df.drop(refNum)

    matcherFunc = ORBRegisterTransform if fast else SIFTRegisterTransform

    matchTime = time.time()
    print("Start Match")
    trans, animation = matcherFunc(refRow.data.data.mean(axis=2), [row.data.data.mean(axis=2) for i, row in df.iterrows()], debugPlots=True)
    print(f"Matching took {time.time() - matchTime} seconds")

    df['transforms'] = trans
    a = 1  # Breakpoint

    # measure average spectrum over a fine grid of the transformed image.