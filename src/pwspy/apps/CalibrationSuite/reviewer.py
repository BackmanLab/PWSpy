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

        # Use the cube splitter to view scores at a smaller scale
        # idx = 1
        # slc = self.resultPairs[idx][1].getValidDataSlice()
        # arr1 = self.resultPairs[idx][1].transformedData[slc]
        # arr2 = self._loader.template.analysisResults.reflectance.data + self._loader.template.analysisResults.meanReflectance[:, :, None]
        # arr2 = arr2[slc]
        # c = DualCubeSplitter(arr2, arr1)
        # def score(arr1, arr2):
        #     comb = MSEScorer(arr1, arr2)
        #     return comb.score()
        # for factor in range(1, 5):
        #     out = c.apply(score, factor)
        #     plt.figure()
        #     plt.imshow(out, cmap='gray')
        #     plt.colorbar()
        # a = 1

        # View the full SSIM result array
        # idx = 0
        # slc = self.resultPairs[idx][1].getValidDataSlice()
        # arr1 = self.resultPairs[idx][1].transformedData[slc]
        # arr2 = self._loader.template.analysisResults.reflectance.data + self._loader.template.analysisResults.meanReflectance[:, :, None]
        # arr2 = arr2[slc]
        # from skimage.metrics import structural_similarity
        # score, full = structural_similarity(arr2, arr1, full=True)
        # p = PlotNd(full)
        # a = 1
        # for measurement, result in self.resultPairs:
        #     logger.debug(f"Scoring SubArrays of {measurement.name}")
