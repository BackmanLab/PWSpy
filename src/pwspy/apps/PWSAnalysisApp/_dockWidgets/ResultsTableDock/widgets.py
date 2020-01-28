from typing import Optional, Tuple, Dict

from PyQt5 import QtCore
from PyQt5.QtWidgets import QTableWidgetItem, QPushButton, QApplication
import matplotlib.pyplot as plt

from pwspy.analysis.compilation.abstract import AbstractCompilerSettings
from pwspy.analysis.compilation.dynamics import DynamicsCompilerSettings
from pwspy.analysis.compilation.generic import GenericCompilerSettings
from pwspy.analysis.compilation.pws import PWSCompilerSettings
from pwspy.apps.PWSAnalysisApp._utilities.conglomeratedAnalysis import ConglomerateCompilerResults
from pwspy.apps.PWSAnalysisApp._sharedWidgets.tables import CopyableTable, NumberTableWidgetItem
from pwspy.dataTypes import AcqDir
import os


class ResultsTableItem:
    def __init__(self, results: ConglomerateCompilerResults, acq: AcqDir):
        self.results = results
        self.acq = acq
        cellPath = os.path.split(acq.filePath)[0][len(QApplication.instance().workingDirectory) + 1:]
        cellNumber = int(acq.filePath.split('Cell')[-1])
        self.cellPathLabel = QTableWidgetItem(cellPath)
        self.cellNumLabel = NumberTableWidgetItem(cellNumber)
        # Generic results
        self.roiNameLabel = QTableWidgetItem(results.generic.roi.name)
        self.roiNumLabel = NumberTableWidgetItem(results.generic.roi.number)
        self.roiAreaLabel = NumberTableWidgetItem(results.generic.roiArea)
        # PWS related results
        pws = results.pws
        if pws is not None:
            self.pwsAnalysisNameLabel = QTableWidgetItem(pws.analysisName)
            self.rmsLabel = NumberTableWidgetItem(pws.rms)
            self.reflectanceLabel = NumberTableWidgetItem(pws.reflectance)
            self.polynomialRmsLabel = NumberTableWidgetItem(pws.polynomialRms)
            self.autoCorrelationSlopeLabel = NumberTableWidgetItem(pws.autoCorrelationSlope)
            self.rSquaredLabel = NumberTableWidgetItem(pws.rSquared)
            self.ldLabel = NumberTableWidgetItem(pws.ld)
            self.opdButton = QPushButton("OPD")
            self.opdButton.released.connect(self._plotOpd)
            if pws.opd is None:
                self.opdButton.setEnabled(False)
            self.meanSigmaRatioLabel = NumberTableWidgetItem(pws.varRatio)
        else:
            self.pwsAnalysisNameLabel = QTableWidgetItem()
            self.rmsLabel, self.reflectanceLabel, self.polynomialRmsLabel, self.autoCorrelationSlopeLabel, self.rSquaredLabel, self.ldLabel, self.meanSigmaRatioLabel = (NumberTableWidgetItem() for i in range(7))
            self.opdButton = QPushButton("OPD")
            self.opdButton.setEnabled(False)
        # Dynamics related results
        dyn = results.dyn
        if dyn is not None:
            self.dynamicsAnalysisNameLabel = QTableWidgetItem(dyn.analysisName)
            self.rms_tLabel = NumberTableWidgetItem(dyn.rms_t)
            self.dynamicsReflectanceLabel = NumberTableWidgetItem(dyn.reflectance)
        else:
            self.rms_tLabel, self.dynamicsReflectanceLabel = (NumberTableWidgetItem() for i in range(2))
            self.dynamicsAnalysisNameLabel = QTableWidgetItem()


    def _plotOpd(self):
        fig, ax = plt.subplots()
        ax.plot(self.results.pws.opdIndex, self.results.pws.opd)
        fig.suptitle(f"{self.cellPathLabel.text()}/Cell{self.cellNumLabel.text()}")
        fig.show()


class ResultsTable(CopyableTable):
    itemsCleared = QtCore.pyqtSignal()

    # Columns. In the form `name`: (`defaultVisible`, `analysisFieldName`, `compilerSettingsClass, `tooltip`)
    columns: Dict[str, Tuple[bool, Optional[str], Optional[AbstractCompilerSettings], Optional[str]]]
    columns = {
        "Path": (False, None, None, None),
        'Cell#': (True, None, None, None),
        "PWSAnalysis": (False, None, None, None),
        'ROI Name': (True, None, None, None),
        'ROI#': (True, None, None, None),
        "RMS": (True, 'rms', PWSCompilerSettings, "Primary analysis result indicating nanoscopic RI heterogeneity of sample in ROI. Defined as StdDev of the spectra"),
        'Reflectance': (True, 'reflectance', PWSCompilerSettings, "Sample reflectance averaged over the spectrum. Calculated by dividing the acquired image cube by a reference cube and then multiplying by the expected reflectance of the reference. The expected reflectance is determined by the user's choice of reference material in the analysis settings."),
        'ld': (False, 'ld', PWSCompilerSettings, "Referred to as Disorder Strength. This is proportional to RMS / AutoCorr Slope. Due to the noisiness of AutoCorr Slope this is also not very useful."),
        "AutoCorr Slope": (False, 'autoCorrelationSlope', PWSCompilerSettings, "Slope of the natural logarithm of the autocorrelation of the spectra, This is very susceptible to noise, not very useful."),
        'R^2': (False, 'rSquared', PWSCompilerSettings, "A measure the linearity of the slope of the natural logarithm of the autocorrelation function. If this is low then the AutoCorr Slope value should not be trusted."),
        'OPD': (False, 'opd', PWSCompilerSettings, "This is the Fourier transform of the spectrum. In theory this should indicate how much of the signal is contributed to by different optical path differences (OPD). Fun fact, RMS is equal to the integral of the OPD over wavenumber (k), if you are interested only in the RMS due to a specific range of OPD you can get this from summing over the appropriate range of the OPD. This is useful for removing unwanted contributions to RMS from thin films."),
        "Mean Spectra Ratio": (False, 'meanSigmaRatio', PWSCompilerSettings, "The spectral variations that we are interested in are expected to have a short spatial correlation length (neighboring pixels should not have the same spectra. However if we look at the average spectra over a cell nucleus we find that there is an overarching spectra common to the whole region. This is a measure of how much this `mean spectra` contributes to the RMS of the ROI."),
        "Poly RMS": (False, 'polynomialRms', PWSCompilerSettings, "In order to remove spectral features that are not due to interference (fluorescence, absorbance, etc.) we sometimes subtract a polynomial fit from the data before analysis. This indicates the StdDev of the polynomial fit. It's not clear how this is useful"),
        "Roi Area": (False, 'roiArea', GenericCompilerSettings, "The area of the ROI given in units of pixels. This can be converted to microns if you know the size in object space of a single pixel"),
        "Dynamics Analysis": (False, None, None, None),
        "RMS_t": (False, 'rms_t', DynamicsCompilerSettings, "This is the primary analysis result for `Dynamics`. It is the standard deviation of the signal over time when looking at just a single wavelength."),
        "Dynamics Reflectance": (False, 'meanReflectance', DynamicsCompilerSettings, "This is the average reflectance of the ROI for the `Dynamics` measurement.")
    }

    def __init__(self):
        super().__init__()
        self.setRowCount(0)
        self.setColumnCount(len(self.columns.keys()))
        self.setHorizontalHeaderLabels(self.columns.keys())
        for i, (default, settingsName, compilerClass, tooltip) in enumerate(self.columns.values()):
            self.setColumnHidden(i, not default)
            self.horizontalHeaderItem(i).setToolTip(tooltip)
        self.verticalHeader().hide()
        self.setSortingEnabled(True)
        self._items = []

    def addItem(self, item: ResultsTableItem) -> None:
        row = len(self._items)
        # The fact that we are adding items assuming its the last row is a problem if sorting is on.
        self.setSortingEnabled(False)
        self.setRowCount(row + 1)

        self.setItem(row, 0, item.cellPathLabel)
        self.setItem(row, 1, item.cellNumLabel)
        self.setItem(row, 2, item.pwsAnalysisNameLabel)
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
        self.setItem(row, 14, item.dynamicsAnalysisNameLabel)
        self.setItem(row, 15, item.rms_tLabel)
        self.setItem(row, 16, item.dynamicsReflectanceLabel)

        self.setSortingEnabled(True)
        self._items.append(item)

    def clearCellItems(self) -> None:
        self.clearContents()
        self.setRowCount(0)
        self._items = []
        self.itemsCleared.emit()


