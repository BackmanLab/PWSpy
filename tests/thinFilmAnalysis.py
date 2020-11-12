# -*- coding: utf-8 -*-
"""
Created on Fri Nov  6 15:57:44 2020

@author: backman05
"""
from glob import glob
from pwspy import dataTypes as pwsdt
from pwspy.analysis.pws import PWSAnalysis, PWSAnalysisSettings
import pandas as pd

files = glob("Cell*")
acqs = [pwsdt.AcqDir(f) for f in files]

nums = [int(acq.filePath.split("Cell")[-1]) for acq in acqs]

df = pd.DataFrame({'acq': acqs}, index=nums)

ref = df.loc[999].acq.pws.toDataClass()
ref.correctCameraEffects()
ref.normalizeByExposure()
ref.filterDust(1)

df = df.loc[[1, 2, 3, 4, 5]]


def normalize(row):
    print(f"Normalize {row}")
    data: pwsdt.ImCube = row.acq.pws.toDataClass()
    data.correctCameraEffects()
    data.normalizeByExposure()
    data.normalizeByReference(ref)
    return data


df['data'] = df.apply(normalize, axis=1)