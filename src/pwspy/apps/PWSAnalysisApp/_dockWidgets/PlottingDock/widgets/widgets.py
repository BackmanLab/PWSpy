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
        self.analysis = analysis
        self.metadata = metadata
        self.data = None
        self.analysisField = None

    def changeData(self, field):
        if field != self.analysisField:
            self.analysisField = field
            if field == 'imbd': #Load the imbd from the ICMetadata object
                self.data = self.metadata.getImBd()
            else:
                if self.analysis is None:
                    raise ValueError(f"Analysis Plotter for ImCube {self.metadata.filePath} does not have an analysis file.")
                self.data = getattr(self.analysis, field)
            assert len(self.data.shape) == 2
