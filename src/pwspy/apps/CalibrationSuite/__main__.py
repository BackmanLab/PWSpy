from pwspy.apps.CalibrationSuite._utility import CubeSplitter
from pwspy.apps.CalibrationSuite.analyzer import ITOAnalyzer
import os
import logging
import sys
import matplotlib.pyplot as plt

from pwspy.apps.CalibrationSuite.loaders import DateMeasurementLoader
from pwspy.utility.plotting import PlotNd
import pandas as pd
import numpy as np


def configureLogger():
    logger = logging.getLogger("pwspy")  # We get the root logger so that all loggers in pwspy will be handled.
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    return logger


def main():
    plt.ion()

    directory = r'\\BackmanLabNAS\home\Year3\ITOPositionStability\AppTest'

    logger = configureLogger()

    logger.debug("Start ITO Analyzer")
    loader = DateMeasurementLoader(directory, os.path.join(directory, '10_20_2020'))
    app = ITOAnalyzer(loader)
    logger.debug("Comparing")
    ri = 1  # Random index
    # comp = CubeComparer(app._template.analysisResults.reflectance.data, app._data.iloc[ri].reflectance[0])
    # from scipy.signal import correlate
    # out = correlate(comp._template, comp._test, method='direct')  # Need to do something about the nans before this will work
    c = CubeSplitter(app._template.analysisResults.reflectance.data[:-12,:-13, :])
    clim = (np.percentile(c._arr.mean(axis=2), 1), np.percentile(c._arr.mean(axis=2), 99))
    plt.figure()
    plt.imshow(c._arr.mean(axis=2), clim=clim)
    factors = [1, 2, 3]
    for factor in factors:
        subArrs = c.subdivide(factor)
        fig, axs = plt.subplots(2**factor, 2**factor)
        for i, subArrList in enumerate(subArrs):
            for j, subArr in enumerate(subArrList):
                axs[i, j].imshow(subArr.mean(axis=2), clim=clim)

    a = 1  # Debug Breakpoint

if __name__ == '__main__':
    main()