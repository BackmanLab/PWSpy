import numpy as np

from pwspy.analysis import AnalysisResultsLoader
from pwspy.dataTypes import ICMetaData


class AnalysisPlotter:
    def __init__(self, metadata: ICMetaData, analysis: AnalysisResultsLoader = None):
        self.analysis = analysis
        self.metadata = metadata
        self.data = None
        self.analysisField = None

    def changeData(self, field):
        if field != self.analysisField:
            self.analysisField = field
            if field == 'thumbnail': #Load the thumbnail from the ICMetadata object
                self.data = self.metadata.getThumbnail()
            elif field == 'opdPeak': # Return the opd value corresponding to the max of that pixels opd funtion.
                opd, opdIndex = self.analysis.opd
                self.data = opdIndex[np.argmax(opd, axis=2)]
            else:
                if self.analysis is None:
                    raise ValueError(f"Analysis Plotter for ImCube {self.metadata.filePath} does not have an analysis file.")
                self.data = getattr(self.analysis, field)
            assert len(self.data.shape) == 2
