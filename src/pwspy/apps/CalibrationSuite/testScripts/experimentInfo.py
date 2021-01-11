# -*- coding: utf-8 -*-
"""
Created on Tue Jan  5 19:24:03 2021

@author: backman05
"""
workingDirectory = r'\\backmanlabnas.myqnapcloud.com\home\Year3\ITOPositionStability\ITOCalibrationSensitivity'

experiment = {  # A dictionary of the three different detuning types that were done. The first item of each list should corresponde with a measurement at the default system settings (0.52NA and Field Stop open.)
    'translation':
        ['centered',
         'decenter1',
         'decenter2'],
    'centered':
        ['0_52',
         '0_39',
         '0_50',
         '0_55'],
    'fieldstop':
        ['open',
         'barelyClosed',
         'barelyClosed2']
    }