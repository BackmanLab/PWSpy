from pwspy.apps.CalibrationSuite._utility import CVAffineTransform
from pwspy.apps.CalibrationSuite.reviewer import Reviewer
from loader import Loader
import os
import matplotlib.pyplot as plt
from pwspy.utility.plotting import PlotNd
import experimentInfo
import pandas as pd
import numpy as np


if __name__ == '__main__':
    plt.ion()

    #TODO split the SSIM, forget xCorr to save time
    measurementSet = 'xcorr_blurScan'

    loader = Loader(experimentInfo.workingDirectory, measurementSet)
    scoreNames = loader.measurements[0].loadTransformedData(loader.template.idTag).getScoreNames()  # We assume that all measurement shave the same score names.

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
            scores = result.getScore(scoreName).scores
            displacement = CVAffineTransform.fromPartialMatrix(result.affineTransform).translation
            displacement = np.sqrt(displacement[0] ** 2 + displacement[1] ** 2)
            l.append({**scores, 'displacement': displacement, 'name': measurement.name, 'measurement': measurement, 'result': result})

        df = pd.DataFrame(l)

        df['exp'] = df.apply(lambda row: row['name'].split('_')[0], axis=1)
        df['setting'] = df.apply(lambda row: '_'.join(row['name'].split('_')[1:]), axis=1)

        # Generate a column indicating for each experiment which order they should be plotted in based on the contents of the experimentInfo dictionary
        a = df.groupby('exp', as_index=False).apply(
            lambda g: g.apply(
                lambda row: experimentInfo.experiment[g.exp.iloc[0]].index(row.setting), axis=1)
            )
        a.index = a.index.get_level_values(1) # Get the original index back
        df['idx'] = a

        for expName, g in df.groupby('exp'):
            fig, ax = plt.subplots()
            fig.suptitle(expName)
            g = g.sort_values('idx')
            for score in ['mse', 'ssim', 'xcorr']:
                ax.scatter(g.idx, g[score], label=score)
            plt.xticks(ticks=g.idx, labels=g.setting, rotation=20)
            ax.legend()

    a = 1