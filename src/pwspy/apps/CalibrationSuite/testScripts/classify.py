import pandas as pd
import experimentInfo
from pwspy.apps.CalibrationSuite.testScripts.loader import Loader


def loadDataFrame(measurementSet: str, scoreName: str) -> pd.DataFrame:
    loader = Loader(experimentInfo.workingDirectory, measurementSet)
    results = []
    for i in loader.measurements:
        try:
            result = i.loadTransformedData(loader.template.idTag)
        except OSError:
            result = None  # Calibration must have failed. wasn't saved.
        results.append(result)

    l = []
    for result, measurement in zip(results, loader.measurements):
        if result is None:
            continue

        scoreNames = loader.measurements[0].loadTransformedData(
            loader.template.idTag).getScoreNames()  # We assume that all measurements have the same score names.
        assert scoreName in scoreNames, f"Score `{scoreName}` not available. Available: {scoreNames}"
        l.append({'measurementName': measurement.name, 'measurement': measurement, 'result': result, 'score': result.getScore(scoreName)})

    df = pd.DataFrame(l)
    df['experiment'] = df.apply(lambda row: row['measurementName'].split('_')[0], axis=1)
    df['setting'] = df.apply(lambda row: '_'.join(row['measurementName'].split('_')[1:]), axis=1)
    del df['measurementName']

    # Bool tags for training
    df['apertureCentered'] = (df['experiment'] != 'translation') | ((df['experiment'] == 'translation') & (df['setting'] == 'centered'))
    df['naCorrect'] = (df['experiment'] != 'centered') | ((df['experiment'] == 'centered') & (df['setting'] == '0_52'))
    df["fieldStopCorrect"] = (df['experiment'] != 'fieldstop') | ((df['experiment'] == 'fieldstop') & (df['setting'] == 'open'))
    return df

if __name__ == '__main__':
    from sklearn import tree
    import numpy as np

    measurementSet = 'xcorr_blurScan_4'
    scoreName = '2'
    df = loadDataFrame(measurementSet, scoreName)
    print("Loaded frame")
    # Split the `CombinedScore` object into numerical columns that will be used as inputs
    funcDict = {
        'latXCorr': lambda row: row.score.latxcorr.score,
        'latXCorr_cdry': lambda row: row.score.latxcorr.cdrY,
        'latXCorr_cdrx': lambda row: row.score.latxcorr.cdrX,
        'axXCorr': lambda row: row.score.axxcorr.score,
        'axXCorr_cdry': lambda row: row.score.axxcorr.cdr,
        'axXCorr_shift': lambda row: row.score.axxcorr.shift,
        'nrmse': lambda row: row.score.nrmse.score,
        'ssim': lambda row:  row.score.ssim.score,
        'reflectance': lambda row: row.score.reflectance.reflectanceRatio
    }
    for k, v in funcDict.items():
        df[k] = df.apply(v, axis=1)

    classificationCols = ['apertureCentered', 'naCorrect', 'fieldStopCorrect']
    inputCols = list(funcDict.keys())

    inputs = np.array(df[inputCols])
    outputs = np.array(df[classificationCols])

    clsfr = tree.DecisionTreeClassifier()
    clsfr.fit(inputs, outputs)


    a = 1