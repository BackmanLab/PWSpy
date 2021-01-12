
from pwspy.apps.CalibrationSuite.reviewer import Reviewer
from loader import Loader
import os
import matplotlib.pyplot as plt
from pwspy.utility.plotting import PlotNd
import experimentInfo
import pandas as pd

if __name__ == '__main__':
    plt.ion()

    #TODO split the SSIM, forget xCorr to save time
    measurementSet = 'xcorr_blurScan'

    loader = Loader(experimentInfo.workingDirectory, measurementSet)
    for score in (list(range(1,20)) + [None]):
        score = str(score)
        r = Reviewer(loader, 'None')

        # plots = []
        # for i, row in r.df.iterrows():
        #     # fig, ax = plt.subplots()
        #     # fig.suptitle(row.measurement.name)
        #     # im = ax.imshow(row.result.transformedData.mean(axis=2), clim = [0, 40])
        #     # plt.colorbar(im)
        #     plots.append( PlotNd(row.result.transformedData, title=row.measurement.name))

        df = r.df
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