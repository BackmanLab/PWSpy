from __future__ import annotations
from PyQt5 import QtCore
from PyQt5.QtWidgets import QWidget, QGridLayout, QComboBox
from typing import Optional

from dataTypes import AcqDir

from .widgets import AnalysisPlotter
from .bigPlot import BigPlot
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import ICMetaData
from pwspy.analysis import AnalysisResultsLoader



class AnalysisViewer(AnalysisPlotter, QWidget):
    def __init__(self, metadata: AcqDir, analysisLoader: Optional[AnalysisResultsLoader], title: str, parent=None, initialField='thumbnail'):
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        AnalysisPlotter.__init__(self, metadata, analysisLoader)
        self.setWindowTitle(title)
        layout = QGridLayout()
        self.plotWidg = BigPlot(metadata, metadata.pws.getThumbnail(), 'title')
        self.analysisCombo = QComboBox(self)
        items = ['thumbnail']
        for i in ['meanReflectance', 'rms', 'autoCorrelationSlope', 'rSquared', 'ld']:
            try:
                if hasattr(self.analysis, i):  # This will raise a key error if the analysis object exists but the requested item is not found
                    items.append(i)
            except KeyError:
                pass
        if self.analysis is not None:
            if 'reflectance' in self.analysis.file.keys(): #This is the normalized 3d data cube. needed to generate the opd.
                items.append('opdPeak')
        if self.metadata.fluorescence is not None:
            items.append('fluorescence')
        self.analysisCombo.addItems(items)
        self.analysisCombo.currentTextChanged.connect(self.changeData)  # If this line comes before the analysisCombo.addItems line then it will get triggered when adding items.
        layout.addWidget(self.analysisCombo, 0, 0, 1, 1)
        layout.addWidget(self.plotWidg, 1, 0, 8, 8)
        self.setLayout(layout)
        self.changeData(initialField)
        self.show()

    def changeData(self, field):
        super().changeData(field)
        if self.analysisCombo.currentText() != field:
            self.analysisCombo.setCurrentText(field)
        self.plotWidg.setImageData(self.data)
        self.plotWidg.setSaturation()

    def setMetadata(self, md: AcqDir, analysis: Optional[AnalysisResultsLoader] = None):
        super().setMetadata(md, analysis)
        self.plotWidg.setMetadata(md)
