from pwspy.apps.CalibrationSuite._utility import CVAffineTransform
from pwspy.apps.CalibrationSuite.loaders import AbstractMeasurementLoader
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


class Reviewer:
    def __init__(self, loader: AbstractMeasurementLoader):
        self._loader = loader
        results = [i.loadCalibrationResult(loader.template.idTag) for i in loader.measurements]

        l = []
        for result, measurement in zip(results, loader.measurements):
            scores = result.scores
            displacement = CVAffineTransform.fromPartialMatrix(result.affineTransform).translation
            displacement = np.sqrt(displacement[0]**2 + displacement[1]**2)
            l.append({**scores, 'displacement': displacement, 'name': measurement.name})

        df = pd.DataFrame(l)

        fig, ax = plt.subplots()
        ax2 = ax.twinx()
        ax.plot(df.mse, label='MSE')
        ax.plot(df.ssim, label='SSIM')
        ax2.plot(df.displacement, label="Displacement (px)", linestyle='--')
        ax.plot(df.xcorr, label="XCorr")
        ax.set_xticklabels(labels=df.name)
        ax.legend()
        ax2.legend()

        #TODO plot correlation with displacement
