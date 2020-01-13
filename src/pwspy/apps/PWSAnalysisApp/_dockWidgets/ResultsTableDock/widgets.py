from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QPushButton, QApplication
import matplotlib.pyplot as plt

from pwspy.analysis.compilation import RoiCompilationResults
from pwspy.apps.PWSAnalysisApp._sharedWidgets.tables import CopyableTable, NumberTableWidgetItem
from pwspy.dataTypes import ICMetaData
import os

class ResultsTableItem:
    def __init__(self, results: RoiCompilationResults, metadata: ICMetaData):
        self.results = results
        self.metadata = metadata
        cellPath = os.path.split(metadata.filePath)[0][len(QApplication.instance().workingDirectory) + 1:]
        cellNumber = int(metadata.acquisitionDirectory.filePath.split('Cell')[-1])
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
        self.roiAreaLabel = NumberTableWidgetItem(results.roiArea)

    def _plotOpd(self):
        fig, ax = plt.subplots()
        ax.plot(self.results.opdIndex, self.results.opd)
        fig.suptitle(f"{self.cellPathLabel.text()}/Cell{self.cellNumLabel.text()}")
        fig.show()


class ResultsTable(CopyableTable):
    itemsCleared = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        #Columns. In the form `name`: (`defaultVisible`, `analysisFieldName`, `tooltip`)
        self.columns = \
            {"Path": (False, None, None),
            'Cell#': (True, None, None),
            "PWSAnalysis": (False, None, None),
            'ROI Name': (True, None, None),
            'ROI#': (True, None, None),
            "RMS": (True, 'rms', "Primary analysis result indicating nanoscopic RI heterogeneity of sample in ROI. Defined as StdDev of the spectra"),
            'Reflectance': (True, 'reflectance', "Sample reflectance averaged over the spectrum. Calculated by dividing the acquired image cube by a reference cube and then multiplying by the expected reflectance of the reference. The expected reflectance is determined by the user's choice of reference material in the analysis settings."),
            'ld': (False, 'ld', "Referred to as Disorder Strength. This is proportional to RMS / AutoCorr Slope. Due to the noisiness of AutoCorr Slope this is also not very useful."),
            "AutoCorr Slope": (False, 'autoCorrelationSlope', "Slope of the natural logarithm of the autocorrelation of the spectra, This is very susceptible to noise, not very useful."),
            'R^2': (False, 'rSquared', "A measure the linearity of the slope of the natural logarithm of the autocorrelation function. If this is low then the AutoCorr Slope value should not be trusted."),
            'OPD': (False, 'opd', "This is the Fourier transform of the spectrum. In theory this should indicate how much of the signal is contributed to by different optical path differences (OPD). Fun fact, RMS is equal to the integral of the OPD over wavenumber (k), if you are interested only in the RMS due to a specific range of OPD you can get this from summing over the appropriate range of the OPD. This is useful for removing unwanted contributions to RMS from thin films."),
            "Mean Spectra Ratio": (False, 'meanSigmaRatio', "The spectral variations that we are interested in are expected to have a short spatial correlation length (neighboring pixels should not have the same spectra. However if we look at the average spectra over a cell nucleus we find that there is an overarching spectra common to the whole region. This is a measure of how much this `mean spectra` contributes to the RMS of the ROI."),
            "Poly RMS": (False, 'polynomialRms', "In order to remove spectral features that are not due to interference (fluorescence, absorbance, etc.) we sometimes subtract a polynomial fit from the data before analysis. This indicates the StdDev of the polynomial fit. It's not clear how this is useful" ),
            "Roi Area": (False, 'roiArea', "The area of the ROI given in units of pixels. This can be converted to microns if you know the size in object space of a single pixel")}
        self.setRowCount(0)
        self.setColumnCount(len(self.columns.keys()))
        self.setHorizontalHeaderLabels(self.columns.keys())
        for i, (default, settingsName, tooltip) in enumerate(self.columns.values()):
            self.setColumnHidden(i, not default)
            self.horizontalHeaderItem(i).setToolTip(tooltip)
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
        self.setItem(row, 13, item.roiAreaLabel)


        self.setSortingEnabled(True)
        self._items.append(item)

    def clearCellItems(self) -> None:
        self.clearContents()
        self.setRowCount(0)
        self._items = []
        self.itemsCleared.emit()


