from PyQt5.QtWidgets import QApplication
from numpy.core import long

from pwspy.apps.CalibrationSuite._utility import CVAffineTransform
from pwspy.apps.CalibrationSuite.reviewer import Reviewer
from loader import Loader
import os
import matplotlib.pyplot as plt
from mpl_qt_viz.visualizers import PlotNd, DockablePlotWindow
import experimentInfo
import pandas as pd
import numpy as np


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
    return df


if __name__ == '__main__':
    import matplotlib as mpl
    # plt.ioff()

    measurementSet = 'xcorr_blurScan_2'

    df = loadDataFrame(measurementSet)
    df = pd.merge(df, experimentInfo.experiment, on=('experiment', 'setting'))
    df['setting'] = df['setting'].apply(lambda val: val.replace('_', '.'))  # Replace the underscores with period to make the NA look better in plots

    scoreNames = [colName.split('_')[0] for colName in df.columns if colName.endswith("_score")]  # Assumes there is no '_' in the score name
    #Sort scorenames numerically
    scoreNameInts = [0 if x=='None' else int(x) for x in scoreNames]
    scoreNameInts, scoreNames = list(zip(*sorted(zip(scoreNameInts, scoreNames))))

    scoreCmap = mpl.cm.nipy_spectral
    scoreColors = scoreCmap(np.linspace(0, 0.95, num=len(scoreNames))) # Clip the ends to avoid the black and white at the ends of the nipy_specal cmap.

    def drawBlurCBar():
        cbar = plt.colorbar(
            mappable=mpl.cm.ScalarMappable(
                norm=mpl.colors.Normalize(min(scoreNameInts), max(scoreNameInts)),
                cmap=scoreCmap))
        cbar.set_label("Blur (px)")

    expSides = {'centered': 'left', 'translation': 'right', 'fieldstop': 'bottom'}
    app = QApplication([])
    expWindow = DockablePlotWindow("Experiment Comparison")
    # Plot NRMSE Score
    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(title=f"NRMSE {expName}", dockArea=expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [i.nrmse.score for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    # Plot SSIM Score
    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"SSIM {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [i.ssim.score for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    # Plot LatXCorr Score
    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"LatXCorr {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [i.latxcorr.score for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    # Plot AxXCorr Score
    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"AxXCorr {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [i.axxcorr.score for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"Axial Shift {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [i.axxcorr.shift for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"Axial CDR {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [i.axxcorr.cdr for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"Lat CDR_x (normed) {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = np.array([i.latxcorr.cdrX for i in scores])
            scores = scores / scores[0] # normalize by first value
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"Lat CDR_y (normed) {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = np.array([i.latxcorr.cdrY for i in scores])
            scores = scores / scores[0] # normalize by first value
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"Lateral Shift {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [np.sqrt(np.sum(np.array(i.latxcorr.shift)**2)) for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    for expName, g in df.groupby('experiment'):
        fig, ax = expWindow.subplots(f"Reflectance {expName}", expSides[expName])
        g = g.sort_values('idx')
        for scoreName, color in zip(scoreNames, scoreColors):
            scores = g[f"{scoreName}_score"]
            scores = [i.reflectance.reflectanceRatio for i in scores]
            ax.scatter(g.settingQuantity, scores, label=scoreName, color=color)
        plt.xticks(ticks=g.settingQuantity, labels=g.setting, rotation=20)
        drawBlurCBar()

    refCompWindow = DockablePlotWindow("Reference Comparison")

    ### Plots comparing the aligned images to eachother ###
    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("Axial XCorr")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.axxcorr.score for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("Lateral XCorr")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.latxcorr.score for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("NRMSE")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.nrmse.score for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("SSIM")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.ssim.score for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("Lateral CDR_x")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.latxcorr.cdrX for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("Lateral CDR_y")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.latxcorr.cdrY for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("Lateral Shift")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [np.sqrt(np.sum(np.array(i.latxcorr.shift)**2)/2) for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("Axial Shift")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.axxcorr.shift for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    g = df[df.isref]
    g.index = list(range(len(g)))
    fig, ax = refCompWindow.subplots("Reflectance Ratio")
    for scoreName, color in zip(scoreNames, scoreColors):
        scores = g[f"{scoreName}_score"]
        scores = [i.reflectance.reflectanceRatio for i in scores]
        ax.scatter(g.index, scores, label=scoreName, color=color)
    plt.xticks(ticks=g.index, labels=g.experiment, rotation=20)
    drawBlurCBar()

    app.exec()
    a = 1
