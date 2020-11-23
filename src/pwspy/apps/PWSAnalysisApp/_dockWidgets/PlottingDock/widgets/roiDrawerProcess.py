from __future__ import annotations
from PyQt5.QtWidgets import QMessageBox, QApplication
import typing
from pwspy.dataTypes import Roi, AcqDir

if typing.TYPE_CHECKING:
    from pwspy.apps.PWSAnalysisApp._dockWidgets.PlottingDock.widgets.analysisViewer import AnalysisViewer


class RoiSaverController:
    """
    This class used to pass information to a separate process and thread to try to make saving ROIs less disruptive to the UI. It didn't really work.
    Rois are now much faster to save anyway so this file has been greatly simplified.
    
    Args:
        anViewer: A reference to an analysis viewer widget that we draw ROI's on.
    """
    def __init__(self, anViewer: AnalysisViewer):
        self.anViewer = anViewer

    def saveNewRoi(self, name: str, num: int, verts, datashape, acq: AcqDir):
        roi = Roi.fromVerts(name, num, verts, datashape)
        try:
            acq.saveRoi(roi)
            self.anViewer.addRoi(roi)
            self._roiIsSaved()
        except OSError:
            self._overWriteRoi(acq, roi)
        self.anViewer.canvas.draw_idle()

    def _overWriteRoi(self, acq: AcqDir, roi: Roi):
        """If the worker raised an `OSError` then we need to ask the user if they want to overwrite."""
        ans = QMessageBox.question(self.anViewer, 'Overwrite?', f"Roi {roi.name}:{roi.number} already exists. Overwrite?")
        if ans == QMessageBox.Yes:
            acq.saveRoi(roi, overwrite=True)
            self.anViewer.showRois() #Refresh all rois since we just deleted one as well.
            self._roiIsSaved()

    def _roiIsSaved(self):
        """Either way, once a  new roi has been saved we want to do this."""
        QApplication.instance().window.cellSelector.refreshCellItems()  # Refresh the cell selection table.
