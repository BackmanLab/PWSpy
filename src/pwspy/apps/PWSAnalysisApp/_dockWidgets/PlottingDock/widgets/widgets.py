from typing import Optional
import numpy as np

from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateAnalysisResults
from pwspy.dataTypes import AcqDir, FluorescenceImage
from enum import Enum


class _AnalysisTypes(Enum):
    """An Enumeration of the possible analysis types."""
    PWS = "pws"
    DYN = "dyn"


class _PlotFields(Enum):
    """An enumerator of the possible images that can be displayed.
    The first item of each tuple indicates which analysis must be available for the image to be displayed.
    The second item of each tuple is a string value matching the attribute name of the associated analysisResults class."""
    Thumbnail = (None, 'thumbnail')
    Fluorescence = (None, 'fluorescence')
    #PWS specific
    OpdPeak = (_AnalysisTypes.PWS, 'opdPeak')
    MeanReflectance = (_AnalysisTypes.PWS, 'meanReflectance')
    RMS = (_AnalysisTypes.PWS, 'rms')
    AutoCorrelationSlope = (_AnalysisTypes.PWS, 'autoCorrelationSlope')
    RSquared = (_AnalysisTypes.PWS, 'rSquared')
    Ld = (_AnalysisTypes.PWS, 'ld')
    #Dynamics specific
    RMS_t_squared = (_AnalysisTypes.DYN, 'rms_t_squared')
    Diffusion = (_AnalysisTypes.DYN, 'diffusion')
    DynamicsReflectance = (_AnalysisTypes.DYN, 'meanReflectance')

class AnalysisPlotter:



    def __init__(self, acq: AcqDir, analysis: ConglomerateAnalysisResults = None):
        self.analysisField: AnalysisPlotter.PlotFields = None
        self.analysis: ConglomerateAnalysisResults = analysis
        self.acq: AcqDir = acq
        self.data: np.ndarray = None

    def changeData(self, field: _PlotFields):
        assert isinstance(field, AnalysisPlotter.PlotFields)
        self.analysisField = field
        if field is _PlotFields.Thumbnail:  # Load the thumbnail from the ICMetadata object
            self.data = self.acq.getThumbnail()
        elif field is _PlotFields.Fluorescence: #Open the fluorescence image.
            self.data = FluorescenceImage.fromMetadata(self.acq.fluorescence).data
        else:
            anType, paramName = field.value
            if anType == _AnalysisTypes.PWS:
                analysis = self.analysis.pws
            elif anType == _AnalysisTypes.DYN:
                analysis = self.analysis.dyn
            else:
                raise TypeError("Unidentified analysis type")
            if analysis is None:
                raise ValueError(f"Analysis Plotter for {self.acq.filePath} does not have an analysis file.")
            if field is _PlotFields.OpdPeak:  # Return the index corresponding to the max of that pixel's opd funtion.
                opd, opdIndex = self.analysis.pws.opd
                self.data = opdIndex[np.argmax(opd, axis=2)]
            else:
                self.data = getattr(analysis, paramName)
        assert len(self.data.shape) == 2

    def setMetadata(self, md: AcqDir, analysis: Optional[ConglomerateAnalysisResults] = None):
        self.analysis = analysis
        self.acq = md
        self.changeData(self.analysisField)

