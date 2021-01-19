import pandas as pd
import experimentInfo
from pwspy.apps.CalibrationSuite.testScripts.loader import Loader


def loadDataFrame(measurementSet: str) -> pd.DataFrame:
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
        assert len(scoreNames) == 1
        l.append({'measurementName': measurement.name, 'measurement': measurement, 'result': result, 'score': result.getScore(scoreNames[0])})

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
    measurementSet = 'xcorr_gogo'
    df = loadDataFrame(measurementSet)