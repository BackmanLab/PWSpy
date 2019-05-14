from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QPushButton, QApplication
import matplotlib.pyplot as plt

from pwspy.analysis.compilation.roiCompilationResults import RoiCompilationResults
from pwspy.apps.PWSAnalysisApp.sharedWidgets.tables import CopyableTable, NumberTableWidgetItem
from pwspy.imCube.ICMetaDataClass import ICMetaData
import os

class ResultsTableItem:
    def __init__(self, results: RoiCompilationResults, metadata: ICMetaData):
        self.results = results
        self.metadata = metadata
        cellPath = os.path.split(metadata.filePath)[0][len(QApplication.instance().workingDirectory) + 1:]
        cellNumber = int(metadata.filePath.split('Cell')[-1])
        self.cellPathLabel = QTableWidgetItem(cellPath)
        self.cellNumLabel = NumberTableWidgetItem(cellNumber)
        self.analysisNameLabel = QTableWidgetItem(results.analysisName)
        self.roiNameLabel = QTableWidgetItem(results.roi.name)
        self.roiNumLabel = NumberTableWidgetItem(results.roi.number)
        self.rmsLabel = NumberTableWidgetItem(results.rms)
        self.reflectanceLabel = NumberTableWidgetItem(results.reflectance)
        self.polynomialRmsLabel = NumberTableWidgetItem(results.polynomialRms)
        self.autoCorrelationSlopeLabel = NumberTableWidgetItem(results.autoCorrelationSlope)
        self.rSquaredLabel = NumberTableWidgetItem(results.rSquared)
        self.ldLabel = NumberTableWidgetItem(results.ld)
        self.opdButton = QPushButton("OPD")
        self.opdButton.released.connect(self._plotOpd)
        if results.opd is None:
            self.opdButton.setEnabled(False)
        self.meanSigmaRatioLabel = NumberTableWidgetItem(results.varRatio)

    def _plotOpd(self):
        fig, ax = plt.subplots()
        ax.plot(self.results.opdIndex, self.results.opd)
        fig.suptitle(f"{self.cellPathLabel.text()}/Cell{self.cellNumLabel.text()}")
        fig.show()


class ResultsTable(CopyableTable):
    itemsCleared = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.columns = \
            {"Path": (False, None), 'Cell#': (True, None), "Analysis": (False, None), 'ROI Name': (True, None),
            'ROI#': (True, None), "RMS": (True, 'rms'), 'Reflectance': (True, 'reflectance'), 'ld': (False, 'ld'),
            "AutoCorr Slope": (False, 'autoCorrelationSlope'), 'R^2': (False, 'rSquared'), 'OPD': (False, 'opd'),
            "Mean Spectra Ratio": (False, 'meanSigmaRatio'), "Poly RMS": (False, 'polynomialRms')}
        self.setRowCount(0)
        self.setColumnCount(len(self.columns.keys()))
        self.setHorizontalHeaderLabels(self.columns.keys())
        for i, (default, settingsName) in enumerate(self.columns.values()):
            self.setColumnHidden(i, not default)
        self.verticalHeader().hide()
        self.setSortingEnabled(True)
        self._items = []

    def addItem(self, item: ResultsTableItem) -> None:
        row = len(self._items)
        # The fact that we are adding items assuming its the last row is a problem is sorting is on.
        self.setSortingEnabled(False)
        self.setRowCount(row + 1)

        self.setItem(row, 0, item.cellPathLabel)
        self.setItem(row, 1, item.cellNumLabel)
        self.setItem(row, 2, item.analysisNameLabel)
        self.setItem(row, 3, item.roiNameLabel)
        self.setItem(row, 4, item.roiNumLabel)
        self.setItem(row, 5, item.rmsLabel)
        self.setItem(row, 6, item.reflectanceLabel)
        self.setItem(row, 7, item.ldLabel)
        self.setItem(row, 8, item.autoCorrelationSlopeLabel)
        self.setItem(row, 9, item.rSquaredLabel)
        self.setCellWidget(row, 10, item.opdButton)
        self.setItem(row, 11, item.meanSigmaRatioLabel)
        self.setItem(row, 12, item.polynomialRmsLabel)


        self.setSortingEnabled(True)
        self._items.append(item)

    def clearCellItems(self) -> None:
        self.clearContents()
        self.setRowCount(0)
        self._items = []
        self.itemsCleared.emit()


