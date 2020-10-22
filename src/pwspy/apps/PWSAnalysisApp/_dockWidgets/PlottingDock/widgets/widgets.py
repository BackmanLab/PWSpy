# Copyright 2018-2020 Nick Anthony, Backman Biophotonics Lab, Northwestern University
#
# This file is part of PWSpy.
#
# PWSpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# PWSpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with PWSpy.  If not, see <https://www.gnu.org/licenses/>.

from typing import Optional
import numpy as np

from pwspy.apps.PWSAnalysisApp.utilities.conglomeratedAnalysis import ConglomerateAnalysisResults
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
    Fluorescence0 = (None, 'fluorescence0')
    Fluorescence1 = (None, 'fluorescence1')
    Fluorescence2 = (None, 'fluorescence2')
    Fluorescence3 = (None, 'fluorescence3')
    Fluorescence4 = (None, 'fluorescence4')
    Fluorescence5 = (None, 'fluorescence5')
    Fluorescence6 = (None, 'fluorescence6')
    Fluorescence7 = (None, 'fluorescence7')
    Fluorescence8 = (None, 'fluorescence8')
    Fluorescence9 = (None, 'fluorescence9')  # Hopefully we never need nearly this many.
    # PWS specific
    OpdPeak = (_AnalysisTypes.PWS, 'opdPeak')  # Even though this isn't really a name of an analysis field we need something unique for this enum value.
    SingleWavelength = (_AnalysisTypes.PWS, 'singleWavelength')
    MeanReflectance = (_AnalysisTypes.PWS, 'meanReflectance')
    RMS = (_AnalysisTypes.PWS, 'rms')
    AutoCorrelationSlope = (_AnalysisTypes.PWS, 'autoCorrelationSlope')
    RSquared = (_AnalysisTypes.PWS, 'rSquared')
    Ld = (_AnalysisTypes.PWS, 'ld')
    # Dynamics specific
    RMS_t_squared = (_AnalysisTypes.DYN, 'rms_t_squared')
    Diffusion = (_AnalysisTypes.DYN, 'diffusion')
    DynamicsReflectance = (_AnalysisTypes.DYN, 'meanReflectance')


_FluorescencePlotFields = [_PlotFields.Fluorescence0, _PlotFields.Fluorescence1, _PlotFields.Fluorescence2,
                           _PlotFields.Fluorescence3, _PlotFields.Fluorescence4, _PlotFields.Fluorescence5,
                           _PlotFields.Fluorescence6, _PlotFields.Fluorescence7, _PlotFields.Fluorescence8,
                           _PlotFields.Fluorescence9, ]


class AnalysisPlotter:
    PlotFields = _PlotFields
    _fluorescencePlotFields = _FluorescencePlotFields

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
        elif field in _FluorescencePlotFields:  # Open the fluorescence image.
            idx = _FluorescencePlotFields.index(field)  # Get the number for the fluorescence image that has been selected.
            self.data = FluorescenceImage.fromMetadata(self.acq.fluorescence[idx]).data
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
            elif field is _PlotFields.SingleWavelength:  # Return the image of the middle wavelength reflectance.
                _ = self.analysis.pws.reflectance.data
                self.data = _[:, :, _.shape[2]//2] # + self.analysis.pws.meanReflectance # It actually looks better without the meanReflectance added
            else:
                self.data = getattr(analysis, paramName)
        assert len(self.data.shape) == 2

    def setMetadata(self, md: AcqDir, analysis: Optional[ConglomerateAnalysisResults] = None):
        self.analysis = analysis
        self.acq = md
        self.changeData(self.analysisField)

