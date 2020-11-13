
if __name__ == '__main__':
    from pwspy.apps.CalibrationSuite.analyzer import ITOAnalyzer
    import os
    import logging
    import sys
    import matplotlib.pyplot as plt

    plt.ion()

    directory = r'\\BackmanLabNAS\home\Year3\ITOPositionStability\AppTest'

    logger = logging.getLogger("pwspy")  # We get the root logger so that all loggers in pwspy will be handled.
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.debug("Start ITO Analyzer")
    app = ITOAnalyzer(directory, os.path.join(directory, '10_20_2020'))
    a = 1