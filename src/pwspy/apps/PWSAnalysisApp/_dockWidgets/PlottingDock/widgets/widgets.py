from typing import Optional
import numpy as np
from pwspy.dataTypes import AcqDir
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.dataTypes import ICMetaData
from enum import Enum, auto



class AnalysisPlotter:
    class PlotFields(Enum):
        """An enumerator of the possible images that can be displayed."""
        Thumbnail = 'thumbnail'
        OpdPeak = 'opdPeak'
        Fluorescence = 'fluorescence'
        MeanReflectance = 'meanReflectance'
        RMS = 'rms'
        AutoCorrelationSlope = 'autoCorrelationSlope'
        RSquared = 'rSquared'
        Ld = 'ld'

    def __init__(self, metadata: AcqDir, analysis: PWSAnalysisResults = None):
        self.analysisField = None
        self.analysis = analysis
        self.metadata = metadata
        self.data = None

    def changeData(self, field: PlotFields):
        assert isinstance(field, AnalysisPlotter.PlotFields)
        self.analysisField = field
        if field is self.PlotFields.Thumbnail:  # Load the thumbnail from the ICMetadata object
            self.data = self.metadata.getThumbnail()
        elif field is self.PlotFields.OpdPeak: # Return the opd value corresponding to the max of that pixels opd funtion.
            if self.analysis is None:
                raise ValueError(f"Analysis Plotter for {self.metadata.filePath} does not have an analysis file.")
            opd, opdIndex = self.analysis.opd
            self.data = opdIndex[np.argmax(opd, axis=2)]
        elif field is self.PlotFields.Fluorescence: #Open the fluorescence image.
            self.data = self.metadata.fluorescence.data
        else:
            if self.analysis is None:
                raise ValueError(f"Analysis Plotter for {self.metadata.filePath} does not have an analysis file.")
            self.data = getattr(self.analysis, field.value)
        assert len(self.data.shape) == 2

    def setMetadata(self, md: AcqDir, analysis: Optional[PWSAnalysisResults] = None):
        self.analysis = analysis
        self.metadata = md
        self.changeData(self.analysisField)

