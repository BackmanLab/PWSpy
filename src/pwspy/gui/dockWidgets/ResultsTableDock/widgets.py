from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QPushButton
from matplotlib.backends.backend_qt5 import FigureCanvasQT
from matplotlib.figure import Figure

from pwspy.analysis.compilation.roiCompilationResults import RoiAnalysisResults
from pwspy.gui.sharedWidgets import CopyableTable
from pwspy.gui.sharedWidgets.tables import NumberTableWidgetItem
from pwspy.imCube.ICMetaDataClass import ICMetaData


class ResultsTableItem:
    def __init__(self, results: RoiAnalysisResults, meta: ICMetaData ):
        self.results = results
        self.cellPathLabel = QTableWidgetItem(results.cellPath)
        self.cellNumLabel = NumberTableWidgetItem(results.cellNumber)
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

    def _plotOpd(self):
        fig = Figure()
        ax = fig.add_subplot(1, 1, 1)
        canvas = FigureCanvasQT(fig)
        ax.plot(self.results.opdIndex, self.results.opd)
        canvas.show()

class ResultsTable(CopyableTable):
    itemsCleared = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        columns = ("CellPath", 'Cell#', "Analysis", 'ROI', 'ROI#', "RMS", 'Reflectance', 'ld', "AutoCorr Slope", 'R<sup>2</sup>', 'OPD')
        self.setRowCount(0)
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
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
        self.setItem(row, 7, item.polynomialRmsLabel)
        self.setItem(row, 8, item.autoCorrelationSlopeLabel)
        self.setItem(row, 9, item.rSquaredLabel)
        self.setItem(row, 10, item.ldLabel)
        self.setCellWidget(row, 11, item.opdButton)

        self.setSortingEnabled(True)
        self._items.append(item)

    def clearCellItems(self) -> None:
        self.setRowCount(0)
        self._items = []
        self.itemsCleared.emit()


