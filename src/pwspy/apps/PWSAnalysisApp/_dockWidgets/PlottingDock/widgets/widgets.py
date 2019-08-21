from typing import Optional

import numpy as np
from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QApplication

from pwspy.analysis import AnalysisResultsLoader
from pwspy.dataTypes import ICMetaData


class AspectRatioWidget(QWidget):
    def __init__(self, aspect: float, parent: QWidget = None):
        super().__init__(parent)
        self._aspect = aspect

    def resizeEvent(self, event: QtGui.QResizeEvent):
        self._resize(event.size().width())

    def _resize(self, width):
        newHeight = width / self._aspect
        self.setMaximumHeight(newHeight)

    def setAspect(self, aspect: float):
        self._aspect = aspect
        self._resize(self.width())


class AnalysisPlotter:
    def __init__(self, metadata: ICMetaData, analysis: AnalysisResultsLoader = None):
        self.analysisField = None
        self.analysis = analysis
        self.metadata = metadata
        self.data = None

    def changeData(self, field):
        # if field != self.analysisField:
            self.analysisField = field
            if field == 'thumbnail': #Load the thumbnail from the ICMetadata object
                self.data = self.metadata.getThumbnail()
            elif field == 'opdPeak': # Return the opd value corresponding to the max of that pixels opd funtion.
                opd, opdIndex = self.analysis.opd
                self.data = opdIndex[np.argmax(opd, axis=2)]
            elif field == 'fluorescence': #Open the fluorescence image.
                self.data = self.metadata.getFluorescence().data
            else:
                if self.analysis is None:
                    raise ValueError(f"Analysis Plotter for ImCube {self.metadata.filePath} does not have an analysis file.")
                self.data = getattr(self.analysis, field)
            assert len(self.data.shape) == 2

    def setMetadata(self, md: ICMetaData, analysis: Optional[AnalysisResultsLoader] = None):
        self.analysis = analysis
        self.metadata = md
        self.changeData(self.analysisField)

