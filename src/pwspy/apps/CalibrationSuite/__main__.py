from pwspy.apps.CalibrationSuite.analyzer import CubeComparer
from pwspy.apps.CalibrationSuite.analyzer import ITOAnalyzer
import os
import logging
import sys
import matplotlib.pyplot as plt
from pwspy.utility.plotting import PlotNd
import pandas as pd

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
    app = ITOAnalyzer(directory, os.path.join(directory, '10_20_2020'))
    logger.debug("Transforming")
    app.transformData()
    logger.debug("Comparing")
    ri = 1  # Random index
    comp = CubeComparer(app._template.analysisResults.reflectance.data, app._data.iloc[ri].reflectance[0])
    from scipy.signal import correlate
    out = correlate(comp._template, comp._test, method='direct')  # Need to do something about the nans before this will work

    a = 1  # Debug Breakpoint

if __name__ == '__main__':
    main()