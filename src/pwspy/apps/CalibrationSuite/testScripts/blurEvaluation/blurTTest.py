from PyQt5.QtWidgets import QApplication

from pwspy.apps.CalibrationSuite._utility import CVAffineTransform
from pwspy.apps.CalibrationSuite.testScripts import experimentInfo
import pandas as pd
import numpy as np
from pwspy.apps.CalibrationSuite.testScripts.loader import Loader
import sys

"""This script was a waste of time"""

def loadDataFrame(measurementSet: str) -> pd.DataFrame:
    loader = Loader(experimentInfo.workingDirectory, measurementSet)
    scoreNames = loader.measurements[0].loadTransformedData(
        loader.template.idTag).getScoreNames()  # We assume that all measurements have the same score names.

    results = []
    for i in loader.measurements:
        try:
            result = i.loadTransformedData(loader.template.idTag)
        except OSError:
            result = None  # Calibration must have failed. wasn't saved.
        results.append(result)

    l = []
    l2 = []
    for result, measurement in zip(results, loader.measurements):
        if result is None:
            continue
        displacement = CVAffineTransform.fromPartialMatrix(result.affineTransform).translation
        displacement = np.sqrt(displacement[0] ** 2 + displacement[1] ** 2)
        l.append({'displacement': displacement, 'measurementName': measurement.name, 'measurement': measurement,
                  'result': result})

        scoreDict = {'measurementName': measurement.name}
        for scoreName in scoreNames:
            score = result.getScore(scoreName)
            scoreDict[f"{scoreName}_score"] = score
        l2.append(scoreDict)

    df = pd.DataFrame(l)
    df2 = pd.DataFrame(l2)

    df = pd.merge(df, df2, on='measurementName')
    df['experiment'] = df.apply(lambda row: row['measurementName'].split('_')[0], axis=1)
    df['setting'] = df.apply(lambda row: '_'.join(row['measurementName'].split('_')[1:]), axis=1)
    del df['measurementName']
    df = pd.merge(df, experimentInfo.experiment, on=('experiment', 'setting'))
    df['setting'] = df['setting'].apply(lambda val: val.replace('_', '.'))  # Replace the underscores with period to make the NA look better in plots
    return df


def configureLogger():
    logger = logging.getLogger()  # We get the root logger so that all loggers in pwspy will be handled.
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-4s %(message)s')
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

if __name__ == '__main__':
    import matplotlib.pyplot as plt
    from mpl_qt_viz.visualizers import DockablePlotWindow
    from importlib import reload
    import logging
    reload(logging)

    configureLogger()
    measurementSet = 'xcorr_blurScan_4'
    df = loadDataFrame(measurementSet)
    print("Loaded DataFrame")

    scoreNames = [colName.split('_')[0] for colName in df.columns if colName.endswith("_score")]  # Assumes there is no '_' in the score name
    #Sort scorenames numerically
    scoreNameInts = [0 if x=='None' else int(x) for x in scoreNames]
    scoreNameInts, scoreNames = list(zip(*sorted(zip(scoreNameInts, scoreNames))))

    # Split the `CombinedScore` object into numerical columns that will be used as inputs
    funcDict = {
        'latXCorr': lambda row: row[scoreName].latxcorr.score,
        'latXCorr_cdry': lambda row: row[scoreName].latxcorr.cdrY,
        'latXCorr_cdrx': lambda row: row[scoreName].latxcorr.cdrX,
        'axXCorr': lambda row: row[scoreName].axxcorr.score,
        'axXCorr_cdry': lambda row: row[scoreName].axxcorr.cdr,
        'axXCorr_shift': lambda row: row[scoreName].axxcorr.shift,
        'nrmse': lambda row: row[scoreName].nrmse.score,
        'ssim': lambda row: row[scoreName].ssim.score,
        'reflectance': lambda row: row[scoreName].reflectance.reflectanceRatio
    }
    inputCols = list(funcDict.keys())

    app = QApplication([])
    windows = []
    for col in inputCols:
        w = DockablePlotWindow(col)
        windows.append(w)
        for scoreName in scoreNames:
            fig, ax = w.subplots(scoreName)
            scoreName = f"{scoreName}_score"
            df2 = df[['experiment', 'setting']]
            for k, v in funcDict.items():
                df2[k] = df.apply(v, axis=1)
            df2 = pd.merge(df, df2, on=('experiment', 'setting'))
            _ = df2[df2['isref']]
            ax.scatter(_[col], [0]*len(_), label='aligned')
            _ = df2[~df2['isref']]
            ax.scatter(_[col], [.5]*len(_), marker='^', label='non-aligned')
            plt.legend()
    sys.exit(app.exec())
    a = 1
