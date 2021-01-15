# -*- coding: utf-8 -*-
"""
Created on Tue Jan  5 19:24:03 2021

@author: backman05
"""
import pandas as pd

workingDirectory = r'\\backmanlabnas.myqnapcloud.com\home\Year3\ITOPositionStability\ITOCalibrationSensitivity'

# A dictionary of the three different detuning types that were done.
# The first item of each list should correspond with a measurement at
# the default system settings (0.52NA and Field Stop open.)
# Tuple of the form (settingName, settingQuantity)
experiment = {
    'translation':
        [('centered', 0),
         ('decenter1', 1),
         ('decenter2', 2)],
    'centered':
        [('0_52', .52),
         ('0_39', .39),
         ('0_50', .5),
         ('0_55', .55)],
    'fieldstop':
        [('open', 0),
         ('barelyClosed', 1),
         ('barelyClosed2', 2)]
    }

l = []
for expName, lst in experiment.items():
    for idx, (setting, quant) in enumerate(lst):
        l.append(
            (expName, setting, quant, idx)
        )
experiment = pd.DataFrame(l, columns=['experiment', 'setting', 'settingQuantity', 'idx'])
experiment['isref'] = experiment.idx == 0  # Index 0 measurements correspond to measurements that should have been set ot the correct settings (Field stop open, NA=0.52)
