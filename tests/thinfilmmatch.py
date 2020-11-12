# -*- coding: utf-8 -*-
"""
Created on Mon Oct 26 16:44:06 2020

@author: nick
"""
import traceback
import typing

from pwspy.utility.reflection import Material
import numpy as np

if __name__ == '__main__':
    from glob import glob
    import matplotlib.pyplot as plt
    from pwspy import dataTypes as pwsdt
    import pandas as pd
    import os
    from pwspy.utility.machineVision import SIFTRegisterTransform, ORBRegisterTransform
    import time
    import pwspy.analysis.pws as pwsAnalysis

    fast = True  # Use ORB or SIFT. ORB is much faster but SIFT seems to find more keypoints and is more stable.
    refNum = 3  # The cell number to use as the `template`. other images will be compared to this one.

    plt.ion()
    wDir = r'\\backmanlabnas.myqnapcloud.com\home\Year3\ITOPositionStability'
    files = glob(os.path.join(wDir, "Cell*"))
    acqs = [pwsdt.AcqDir(f) for f in files]

    nums = [int(acq.filePath.split("Cell")[-1]) for acq in acqs]

    df = pd.DataFrame({'acq': acqs}, index=nums)

    ref = df.loc[999].acq.pws.toDataClass()
    ref.correctCameraEffects()
    ref.normalizeByExposure()
    ref.filterDust(1)

    df = df.loc[[1, 2, 3, 4, 5]]

    a = 1  # Breakpoint

    class Matcher:
        def __init__(self, template: pwsAnalysis.PWSAnalysisResults, fastMode: bool = False, debugMode: bool = False):
            self._matcherFunc = ORBRegisterTransform if fastMode else SIFTRegisterTransform
            self._debugMode = debugMode
            self._template = template

        def match(self, ims: typing.Iterable[pwsAnalysis.PWSAnalysisResults]) -> typing.Iterable[np.ndarray]:
            if self._debugMode:
                matchTime = time.time()
                print("Start match.")
            trans, animation = self._matcherFunc(self._template.meanReflectance, [im.meanReflectance for im in ims], debugPlots=self._debugMode)
            if self._debugMode:
                print(f"Matching took {time.time() - matchTime} seconds")
            return trans


    ref = df.loc[999].acq.pws.toDataClass()
    ref.correctCameraEffects()


    settings = pwsAnalysis.PWSAnalysisSettings.loadDefaultSettings("Recommended")
    settings.referenceMaterial = Material.Air
    analysis = pwsAnalysis.PWSAnalysis(settings, extraReflectance=None, ref)


    def normalize(row):
        data: pwsdt.ImCube = row.acq.pws.toDataClass()
        data.correctCameraEffects()
        results, warnings = analysis.run(data)
        return results

    df['results'] = df.apply(normalize, axis=1)
    template = df.results.loc[refNum]
    df = df.drop(refNum)
    matcher = Matcher(template, fastMode=True, debugMode=True)
    df['transform'] = matcher.match(df.results)

    class ITOMeasurement:
        ANALYSIS_NAME = 'ITOCalibration'
        def __init__(self, directory: str, settings: pwsAnalysis.PWSAnalysisSettings):
            self.name = os.path.basename(directory)
            itoAcq = os.path.join(directory, "Cell1")
            self._itoAcq = pwsdt.AcqDir(itoAcq)
            refAcq = os.path.join(directory, "Cell999")
            self._refAcq = pwsdt.AcqDir(refAcq)

            if not self._hasAnalysis():
                self._generateAnalysis(settings)
            else:
                pass # TODO check that settings match the preiously don't analysis

            self._results: pwsAnalysis.PWSAnalysisResults = self._itoAcq.pws.loadAnalysis(self.ANALYSIS_NAME)

        def _generateAnalysis(self, settings: pwsAnalysis.PWSAnalysisSettings):
            ref = self._refAcq.pws.toDataClass()
            ref.correctCameraEffects()
            analysis = pwsAnalysis.PWSAnalysis(settings, None, ref)
            im = self._itoAcq.pws.toDataClass()
            im.correctCameraEffects()
            results = analysis.run(im)
            self._itoAcq.pws.saveAnalysis(results, self.ANALYSIS_NAME)

        def _hasAnalysis(self) -> bool:
            return self.ANALYSIS_NAME in self._itoAcq.pws.getAnalyses()

        @property
        def analysisResults(self) -> pwsAnalysis.PWSAnalysisResults:
            return self._results

        # @property
        # def meanReflectance(self) -> np.ndarray:
        #     return self._results.meanReflectance
        #
        # @property
        # def reflectance(self) -> pwsdt.KCube:
        #     return self._results.reflectance


    class ITOAnalyzer:
        _settings = settings
        def __init__(self, directory: str, templateDirectory: str):
            self._template = ITOMeasurement(templateDirectory, self._settings)

            self._measurements = []
            for f in glob(os.path.join(directory, '*')):
                if os.path.isdir(f):
                    try:
                        self._measurements.append(ITOMeasurement(f, self._settings))
                    except Exception as e:
                        print(f"Failed to load measurement at directory {f}")
                        print(traceback.print_exc())

            self._matcher = Matcher(self._template.analysisResults)
            


    #TODO measure average spectrum over a fine grid of the transformed image.