import pandas as pd
from pwspy.apps.CalibrationSuite.testScripts import experimentInfo
from pwspy.apps.CalibrationSuite.testScripts.loader import Loader
import graphviz
import matplotlib.pyplot as plt
import os


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
    df = pd.merge(df, experimentInfo.experiment, on=('experiment', 'setting'))
    return df


def viewTree(decTree, featNames, classNames, title='temp'):
    # fig = plt.figure()
    # fig.suptitle(title)
    # tree.plot_tree(decTree,
    #                feature_names=featNames,
    #                class_names=classNames,
    #                filled=True)
    dot_data = tree.export_graphviz(decTree, out_file=None,
        feature_names=featNames,
        class_names=classNames,
        filled=True, rounded=True,
        special_characters=True)
    graph = graphviz.Source(dot_data)
    sfx = 0
    while os.path.exists(f"{title}_{sfx}.png"):  # Without this auto-renaming the `view` option causes all calls to show the same image (the last one)
        sfx += 1
    fullPath = f"{title}_{sfx}.png"
    graph.render(filename=fullPath, format='png', view=True)


if __name__ == '__main__':
    from sklearn import tree
    from sklearn.multioutput import MultiOutputClassifier
    import numpy as np
    plt.ion()

    measurementSet = 'xcorr_blurScan_4'
    scoreName = '2'
    df = loadDataFrame(measurementSet, scoreName)
    print("Loaded frame")
    # Split the `CombinedScore` object into numerical columns that will be used as inputs
    funcDict = {
        'latXCorr': lambda row: row.score.latxcorr.score,
        'latXCorr_cdr': lambda row: np.sqrt((row.score.latxcorr.cdrY**2 + row.score.latxcorr.cdrX**2)/2),  # RMS of cdrx and cdry. Looking at data by eye this didn't look that useful, I'm inclined to get rid of it.
        'axXCorr': lambda row: row.score.axxcorr.score,
        'axXCorr_cdr': lambda row: row.score.axxcorr.cdr,
        'axXCorr_shift': lambda row: row.score.axxcorr.shift,
        'nrmse': lambda row: row.score.nrmse.score,
        'ssim': lambda row:  row.score.ssim.score,
        'reflectance': lambda row: row.score.reflectance.reflectanceRatio
    }
    for k, v in funcDict.items():
        df[k] = df.apply(v, axis=1)
    inputCols = list(funcDict.keys())

    # In this case we have a `multilabel` (not `multiclass`) situation. (see: https://scikit-learn.org/stable/modules/multiclass.html)
    # Decision trees are inherently multiclass but we can get multilabel functionality with `MultiOutputClassifier` (which internally creates a tree for each label.
    # 3 Classes
    outputs = pd.DataFrame(
        {'apertureCentered': (df['experiment'] != 'translation') |
                               ((df['experiment'] == 'translation') & df['isref']),
        'naCorrect': (df['experiment'] != 'centered') |
                        ((df['experiment'] == 'centered') & df['isref']),
        "fieldStopCorrect": (df['experiment'] != 'fieldstop') |
                                ((df['experiment'] == 'fieldstop') & df['isref'])
        })
    outputs['isref'] = df.isref
    inputs = df[inputCols]
    mlTree = MultiOutputClassifier(tree.DecisionTreeClassifier())
    mlTree.fit(inputs, outputs)
    for labelName, clsfr in zip(outputs.columns, mlTree.estimators_):
        viewTree(clsfr, inputCols, [f"not_{labelName}", labelName])

    # 5 Classes. We want multilabel, except that the three aperture classes are mutually exclusive (multiclass)
    outputs = [
        pd.DataFrame({'apertureCentered': (df['experiment'] != 'translation') |
                                ((df['experiment'] == 'translation') & df['isref'])}),
        pd.DataFrame({
            'apertureBig': ((df['settingQuantity'] > 0.52) & (df['experiment']=='centered')),
            'apertureSmall': ((df['experiment']=='centered') & (df['settingQuantity'] < 0.52)),
            'naCorrect': (df['experiment'] != 'centered') |
                        ((df['experiment'] == 'centered') & df['isref'])}),
        pd.DataFrame({"fieldStopCorrect": (df['experiment'] != 'fieldstop') |
                                ((df['experiment'] == 'fieldstop') & df['isref'])})
    ]
    inputs = df[inputCols]
    for output in outputs:
        clsfr = tree.DecisionTreeClassifier()
        clsfr.fit(inputs, output)
        outLabels = list(output.columns) if len(output.columns)>1 else [f"not_{output.columns[0]}", output.columns[0]]  # In the case of only one target the tree will treat it as two classes, [not_target, yes_target]
        clsfr.classes_ = outLabels
        viewTree(clsfr, inputCols, outLabels, title=str(outLabels))

    a = 1
