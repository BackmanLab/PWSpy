from typing import Optional

import numpy as np
from pwspy.dataTypes import AcqDir

from pwspy.analysis import AnalysisResultsLoader
from pwspy.dataTypes import ICMetaData


class AnalysisPlotter:
    def __init__(self, metadata: AcqDir, analysis: AnalysisResultsLoader = None):
        self.analysisField = None
        self.analysis = analysis
        self.metadata = metadata
        self.data = None

    def changeData(self, field):
        # if field != self.analysisField:
            self.analysisField = field
            if field == 'thumbnail': #Load the thumbnail from the ICMetadata object
                self.data = self.metadata.pws.getThumbnail()
            elif field == 'opdPeak': # Return the opd value corresponding to the max of that pixels opd funtion.
                opd, opdIndex = self.analysis.opd
                self.data = opdIndex[np.argmax(opd, axis=2)]
            elif field == 'fluorescence': #Open the fluorescence image.
                self.data = self.metadata.fluorescence.data
            else:
                if self.analysis is None:
                    raise ValueError(f"Analysis Plotter for ImCube {self.metadata.filePath} does not have an analysis file.")
                self.data = getattr(self.analysis, field)
            assert len(self.data.shape) == 2

    def setMetadata(self, md: AcqDir, analysis: Optional[AnalysisResultsLoader] = None):
        self.analysis = analysis
        self.metadata = md
        self.changeData(self.analysisField)

