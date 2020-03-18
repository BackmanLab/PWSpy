from __future__ import annotations
import re
import traceback

import numpy as np
from PyQt5 import QtCore
from PyQt5.QtGui import QCursor, QValidator
from PyQt5.QtWidgets import QWidget, QDialog, QVBoxLayout, QDoubleSpinBox, QPushButton, QLabel, QGridLayout, QComboBox, \
    QAction, QMenu, QApplication, QCheckBox
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from pwspy.apps.sharedWidgets.rangeSlider import QRangeSlider
import typing
if typing.TYPE_CHECKING:
    from pwspy.dataTypes import AcqDir


class BigPlot(QWidget):
    def __init__(self, data: np.ndarray, title: str, parent=None):
        """A widget that displays an image."""
        QWidget.__init__(self, parent=parent, flags=QtCore.Qt.Window)
        self.setWindowTitle(title)
        layout = QGridLayout()
        self.fig = Figure()
        self.ax = self.fig.add_subplot(1, 1, 1)
        self.ax.get_yaxis().set_visible(False)
        self.ax.get_xaxis().set_visible(False)
        self.im = self.ax.imshow(data, cmap='gray')
        self.fig.colorbar(self.im, ax=self.ax)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.canvas.setFocus()
        self.fig.subplots_adjust(left=0, bottom=0, right=1, top=1, wspace=0, hspace=0)
        self.slider = QRangeSlider(self)
        self.slider.endValueChanged.connect(self.climImage)
        self.slider.startValueChanged.connect(self.climImage)
        self.autoDlg = SaturationDialog(self)
        self.autoDlg.accepted.connect(self.setSaturation)
        self.rangeDlg = RangeDialog(self)
        self.rangeDlg.accepted.connect(self.setRange)
        self.saturationButton = QPushButton("Auto")
        self.saturationButton.released.connect(self.autoDlg.show)
        self.manualRangeButton = QPushButton("Range")
        self.manualRangeButton.released.connect(self.rangeDlg.show)
        self.cmapCombo = QComboBox(self)
        self.cmapCombo.addItems(['gray', 'jet', 'plasma', 'Reds'])
        self.cmapCombo.currentTextChanged.connect(self.changeCmap)

        layout.addWidget(self.canvas, 0, 0, 8, 8)
        layout.addWidget(QLabel("Color Range"), 9, 0, 1, 1)
        layout.addWidget(self.slider, 9, 1, 1, 4)
        layout.addWidget(self.saturationButton, 9, 6, 1, 1)
        layout.addWidget(self.manualRangeButton, 9, 7, 1, 1)
        layout.addWidget(NavigationToolbar(self.canvas, self), 10, 0, 1, 4)

        layout.addWidget(QLabel("Color Map"), 10, 6, 1, 1, alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.cmapCombo, 10, 7, 1, 1)
        layout.setRowStretch(0, 1)  # This causes the plot to take up all the space that isn't needed by the other widgets.
        l = QVBoxLayout()
        l.addLayout(layout)
        self.setLayout(l)

        self.setImageData(data)
        self.setSaturation()


    def setImageData(self, data: np.ndarray):
        self.data = data
        self.im.set_data(data)
        self.slider.setMax(np.nanmax(self.data))
        self.slider.setMin(np.nanmin(self.data))
        if self.autoDlg.autoSaturateCheckBox.isChecked():
            self.setSaturation()
        self.canvas.draw_idle()

    def setSaturation(self):
        percentage = self.autoDlg.value
        m = np.nanpercentile(self.data, percentage)
        M = np.nanpercentile(self.data, 100 - percentage)
        self.slider.setStart(m)
        self.slider.setEnd(M)

    def setRange(self):
        self.slider.setStart(self.rangeDlg.minimum)
        self.slider.setEnd(self.rangeDlg.maximum)

    def climImage(self):
        self.im.set_clim((self.slider.start(), self.slider.end()))
        self.canvas.draw_idle()

    def changeCmap(self, cMap: str):
        self.im.set_cmap(cMap)
        self.canvas.draw_idle()


class SaturationDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent, flags=QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        l = QGridLayout()
        self.numBox = QDoubleSpinBox()
        self.numBox.setValue(0.1)
        self.numBox.setMinimum(0)
        self.numBox.setSingleStep(0.1)
        self.autoSaturateCheckBox = QCheckBox("Update contrast when image is changed", self)
        self.autoSaturateCheckBox.setChecked(True)
        self.okButton = QPushButton("Ok")
        self.okButton.released.connect(self.accept)
        l.addWidget(QLabel("Saturation %"), 0, 0)
        l.addWidget(self.numBox, 0, 1)
        l.addWidget(self.autoSaturateCheckBox, 1, 0, 1, 2)
        l.addWidget(self.okButton, 2, 0, 1, 2)
        self.setLayout(l)

    @property
    def value(self):
        return self.numBox.value()


class RangeDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent=parent, flags=QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        l = QGridLayout()
        self.minBox = QDoubleSpinBox()

        self.maxBox = QDoubleSpinBox()
        self.okButton = QPushButton("Ok")
        self.okButton.released.connect(self.accept)
        l.addWidget(QLabel("Min"), 0, 0, 1, 1)
        l.addWidget(QLabel("Max"), 0, 1, 1, 1)
        l.addWidget(self.minBox, 1, 0, 1, 1)
        l.addWidget(self.maxBox, 1, 1, 1, 1)
        l.addWidget(self.okButton, 2, 1, 1, 1)
        self.setLayout(l)

    def show(self):
        for b in [self.minBox, self.maxBox]:
            b.setMaximum(self.parent().slider.max())
            b.setMinimum(self.parent().slider.min())
        self.minBox.setValue(self.parent().slider.start())
        self.maxBox.setValue(self.parent().slider.end())
        super().show()

    @property
    def minimum(self): return self.minBox.value()

    @property
    def maximum(self): return self.maxBox.value()


if __name__ == '__main__':
    fPath = r'G:\Aya_NAstudy\matchedNAi_largeNAc\cells\Cell2'
    from pwspy.dataTypes import AcqDir
    acq = AcqDir(fPath)
    import sys
    app = QApplication(sys.argv)
    b = BigPlot(acq, acq.pws.getThumbnail(), "Test")
    b.show()
    sys.exit(app.exec())
