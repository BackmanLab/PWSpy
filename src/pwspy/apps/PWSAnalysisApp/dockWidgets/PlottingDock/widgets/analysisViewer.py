from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QGridLayout, QComboBox
from typing import Optional

from .widgets import AnalysisPlotter
from .bigPlot import BigPlot
from pwspy.imCube import ICMetaData
from pwspy.analysis.analysisResults import AnalysisResultsLoader



class AnalysisViewer(AnalysisPlotter, QWidget):
    def __init__(self, metadata: ICMetaData, analysisLoader: Optional[AnalysisResultsLoader], title: str, parent=None):
        AnalysisPlotter.__init__(self, metadata, analysisLoader)
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        self.setWindowTitle(title)
        layout = QGridLayout()
        self.plotWidg = BigPlot(metadata, metadata.getImBd(), 'title')
        self.analysisCombo = QComboBox(self)
        self.analysisCombo.currentTextChanged.connect(self.changeData)
        self.analysisCombo.addItems(['imbd'] + [i for i in ['meanReflectance', 'rms', 'autoCorrelationSlope', 'rSquared', 'ld'] if hasattr(self.analysis, i)])
        layout.addWidget(self.analysisCombo, 0, 0, 1, 1)
        layout.addWidget(self.plotWidg, 1, 0, 8, 8)
        self.setLayout(layout)
        self.show()

    def changeData(self, field):
        super().changeData(field)
        self.plotWidg.setImageData(self.data)
        self.plotWidg.setSaturation()
