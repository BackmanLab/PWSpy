from __future__ import annotations
import typing as t_
import pandas as pd
from pwspy.dataTypes import ICRawBase, MetaDataBase
from pwspy.utility.fileIO import processParallel
import logging
if t_.TYPE_CHECKING:
    from pwspy.analysis import AbstractAnalysis, AbstractAnalysisResults
    from pwspy.analysis.warnings import AnalysisWarning


class ParallelRunner:
    """
    A utility class for Running an analysis on multiple images in parallel on multiple cores

    Args:
        The analysis object to run.
    """
    def __init__(self, analysis: AbstractAnalysis):
        self._analysis = analysis
        analysis.copySharedDataToSharedMemory()

    def run(self, cubes: t_.List[t_.Union[MetaDataBase, ICRawBase]],
                  saveName: t_.Optional[str] = None) -> t_.List[t_.Tuple[t_.List[AnalysisWarning, AbstractAnalysisResults, MetaDataBase]]]:
        """
        Run an analysis on several images in parallel.

        Args:
            cubes: A list of either data objects or the associated metadata object.s
            saveName: If this name is supplied then the analysis results will be saved under this name for each image.
        """
        out = processParallel(pd.DataFrame({'cube': cubes}), processorFunc=self._process, initializer=self._initializer, initArgs=(self._analysis, saveName))
        return out

    @staticmethod
    def _initializer(analysis: AbstractAnalysis, saveName: t_.Optional[str]):
        """This method is run once for each process that is spawned. it initialized _resources that are shared between each iteration of _process."""
        global pwspyAnalysisParallelGlobals
        pwspyAnalysisParallelGlobals = {'analysis': analysis, 'saveName': saveName}

    @staticmethod
    def _process(rowIndex: int, row: pd.Series):
        """This method is run in parallel. once for each acquisition data that we want to analyze.
        Returns a list of AnalysisWarnings objects with the associated metadat object"""
        global pwspyAnalysisParallelGlobals
        analysis = pwspyAnalysisParallelGlobals['analysis']
        saveName = pwspyAnalysisParallelGlobals['saveName']
        im = row['cube']
        if isinstance(im, MetaDataBase):
            im = im.toDataClass(lock=None)
        results, warnings = analysis.run(im)
        if saveName is not None:
            im.metadata.saveAnalysis(results, saveName, overwrite=True)
        return warnings, results, im.metadata