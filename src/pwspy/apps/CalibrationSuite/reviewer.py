from pwspy.apps.CalibrationSuite._utility import CVAffineTransform
from pwspy.apps.CalibrationSuite.loaders import AbstractMeasurementLoader
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


class Reviewer:
    def __init__(self, loader: AbstractMeasurementLoader):
        self._loader = loader
        results = []
        for i in loader.measurements:
            try:
                result = i.loadCalibrationResult(loader.template.idTag)
            except OSError:
                result = None  # Calibration must have failed. wasn't saved.
            results.append(result)
            

        l = []
        for result, measurement in zip(results, loader.measurements):
            if result is None:
                continue
            scores = result.scores
            displacement = CVAffineTransform.fromPartialMatrix(result.affineTransform).translation
            displacement = np.sqrt(displacement[0]**2 + displacement[1]**2)
            l.append({**scores, 'displacement': displacement, 'name': measurement.name, 'measurement': measurement, 'result': result})

        df = pd.DataFrame(l)
        self.df = df
        fig, ax = plt.subplots()
        ax2 = ax.twinx()
        ax.plot(df.mse, label='MSE')
        ax.plot(df.ssim, label='SSIM')
        x = list(range(len(df.name)))
        ax2.plot(x, df.displacement, label="Displacement (px)", linestyle='--')
        ax.plot(x, df.xcorr, label="XCorr")
        ax.set_xticks(x)
        ax.set_xticklabels(labels=df.name, rotation=20)
        ax.legend()
        ax2.legend()

        # Plot correlation with displacement
        fig, ax = plt.subplots()
        ax.set_xlabel("Displacement")
        ax.set_ylabel("Score")
        fig.suptitle("Displacement vs. Score")
        for s in ['mse', 'ssim', 'xcorr']:
            ax.scatter(df.displacement, df[s], label=s)
