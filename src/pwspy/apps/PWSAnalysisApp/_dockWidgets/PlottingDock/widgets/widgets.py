from typing import Optional
import numpy as np

from pwspy.analysis import AnalysisTypes
from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateAnalysisResults
from pwspy.dataTypes import AcqDir, FluorescenceImage
from pwspy.analysis.pws import PWSAnalysisResults
from pwspy.dataTypes import ICMetaData
from enum import Enum, auto



class AnalysisPlotter:
    class PlotFields(Enum):
        """An enumerator of the possible images that can be displayed. The string values match the attribute names of the associated analysisResults class."""
        Thumbnail = (None, 'thumbnail')
        Fluorescence = (None, 'fluorescence')
        #PWS specific
        OpdPeak = (AnalysisTypes.PWS, 'opdPeak')
        MeanReflectance = (AnalysisTypes.PWS, 'meanReflectance')
        RMS = (AnalysisTypes.PWS, 'rms')
        AutoCorrelationSlope = (AnalysisTypes.PWS, 'autoCorrelationSlope')
        RSquared = (AnalysisTypes.PWS, 'rSquared')
        Ld = (AnalysisTypes.PWS, 'ld')
        #Dynamics specific
        RMS_t = (AnalysisTypes.DYN, 'rms_t')
        Diffusion = (AnalysisTypes.DYN, 'diffusion')
        DynamicsReflectance = (AnalysisTypes.DYN, 'meanReflectance')

    def __init__(self, acq: AcqDir, analysis: ConglomerateAnalysisResults = None):
        self.analysisField: AnalysisPlotter.PlotFields = None
        self.analysis: ConglomerateAnalysisResults = analysis
        self.acq: AcqDir = acq
        self.data: np.ndarray = None

    def changeData(self, field: PlotFields):
        assert isinstance(field, AnalysisPlotter.PlotFields)
        self.analysisField = field
        if field is self.PlotFields.Thumbnail:  # Load the thumbnail from the ICMetadata object
            self.data = self.acq.getThumbnail()
        elif field is self.PlotFields.Fluorescence: #Open the fluorescence image.
            self.data = FluorescenceImage.fromMetadata(self.acq.fluorescence).data
        else:
            if self.analysis is None:
                raise ValueError(f"Analysis Plotter for {self.acq.filePath} does not have an analysis file.")
            if field is self.PlotFields.OpdPeak:  # Return the index corresponding to the max of that pixel's opd funtion.
                if self.analysis is None:
                    raise ValueError(f"Analysis Plotter for {self.acq.filePath} does not have an analysis file.")
                opd, opdIndex = self.analysis.opd
                self.data = opdIndex[np.argmax(opd, axis=2)]
            else:
                anType, paramName = field.value
                if anType == AnalysisTypes.PWS:
                    analysis = self.analysis.pws
                elif anType == AnalysisTypes.DYN:
                    analysis = self.analysis.dyn
                else:
                    raise TypeError("Unidentified analysis type")
                self.data = getattr(analysis, paramName)
        assert len(self.data.shape) == 2

    def setMetadata(self, md: AcqDir, analysis: Optional[ConglomerateAnalysisResults] = None):
        self.analysis = analysis
        self.acq = md
        self.changeData(self.analysisField)

