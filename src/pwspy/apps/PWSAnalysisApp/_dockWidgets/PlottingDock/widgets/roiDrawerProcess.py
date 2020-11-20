import enum
import logging
import multiprocessing as mp
import os
import queue
from datetime import datetime
from time import time
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QThread
from PyQt5.QtWidgets import QWidget, QMessageBox, QApplication
from matplotlib import patches

from pwspy.apps.PWSAnalysisApp import applicationVars
from pwspy.dataTypes import Roi, AcqDir


class _QueueCheckerThread(QObject):
    """The sole purpose of this object is to run in it's own thread on the main process and to check the results queue
    of the child process. Most results from the child process are translated into Qt 'signals' so that the GUI thread can react."""
    roiFinished = pyqtSignal(Roi)  # Fired when an ROI was successfully saved in the child process
    roiNeedsOverwrite = pyqtSignal(AcqDir, Roi)  # Fired when the ROI already existed and could not be saved.

    def __init__(self, resultsQ: mp.Queue):
        super().__init__()
        self._q = resultsQ  # The child process will send us information through this queue.

    @pyqtSlot()
    def doWork(self):
        logger = logging.getLogger(__name__)
        logger.info(f"Starting Roi results thread.")
        while True:
            try:
                resultCode, data = self._q.get(True, .1)  #Periodically check the queue for new information.
                logger.info(f"Received Roi Result from child process")
            except queue.Empty:
                continue
            if resultCode is _Cmd.SUCESS:
                self.roiFinished.emit(data)
            elif resultCode is _Cmd.NEEDSOVERWRITE:
                acq, roi = data
                self.roiNeedsOverwrite.emit(acq, roi)
            elif resultCode is _Cmd.QUIT:
                QThread.currentThread().quit()  # Child process has reported that it is closing, we should close this thread too.
                logger.info(f"Received command to exit ROI thread")
                break
            elif isinstance(resultCode, Exception):
                raise resultCode  # The child process has crashed and returned an error.
            else:
                raise ValueError("Programming Error!")  # This shouldn't happen.


class _Cmd(enum.Enum):
    """An enumeration of possible commands to pass back and forth between processes."""
    SUCESS = enum.auto()
    NEEDSOVERWRITE = enum.auto()
    QUIT = enum.auto()


class _RoiSaverProcess(mp.Process):
    """This class handles the actual saving of the roi and everything that can be performed in a separate process."""
    def __init__(self):
        super().__init__()
        self._q = mp.Queue()  # The child process receives commands through this queue and responds through the other queue.
        self._resultQ = mp.Queue()

    def run(self):
        """This is what gets run in the other process when `start` is called."""
        logger = logging.getLogger("RoiProcess")
        fHandler = logging.FileHandler(os.path.join(applicationVars.dataDirectory, f'RoiProcesslog{datetime.now().strftime("%d%m%Y%H%M%S")}.txt'))
        fHandler.setFormatter(logging.Formatter('%(levelname)s: %(asctime)s %(name)s.%(funcName)s(%(lineno)d) - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(fHandler)
        logger.setLevel(logging.DEBUG)
        logger.info("Process Opened")
        try:
            while True:
                try:
                    item = self._q.get(True, 0.1)  # Periodically check the queue for new commands.
                    logger.info(f"Item received")
                except queue.Empty:
                    continue
                if item is _Cmd.QUIT:  # We received instructions to end the process
                    self._resultQ.put((item, None), False)  # Pass the command back out the queue as confirmation.
                    logger.info("Quitting")
                    break
                name, num, verts, datashape, acq = item  # If we got this far then item must be commands for a new saving.
                logger.info(f"Received ROI {name} {num}")
                sTime = time()
                roi = Roi.fromVerts(name, num, verts, datashape)
                logger.info(f"Roi creation took {time()-sTime} seconds.")
                try:
                    sTime = time()
                    acq.saveRoi(roi)
                    logger.info(f"Roi saving took {time()-sTime} seconds.")
                    self._resultQ.put((_Cmd.SUCESS, roi), False)  # Tell the main process that saving is completed.
                    logger.info(f"Roi placed in queue")
                except OSError:
                    self._resultQ.put((_Cmd.NEEDSOVERWRITE, (acq, roi)), False)  # Tell the main process that there is a file conflict and we need to overwrite the ROI.
        except Exception as e:
            self._resultQ.put((e, None), False)  # pass any errors back to the main process for handling.

    def requestClose(self):
        """Call this from the main process to request that the child process closes."""
        self._q.put(_Cmd.QUIT, True, 0.5)

    def saveNewRoi(self, name: str, num: int, verts, datashape, acq: AcqDir):
        """Call this from the main process to start saving in the saver process."""
        self._q.put((name, num, verts, datashape, acq), True, 0.5)
        logging.getLogger(__name__).info(f"Sent roi {name} {num} to child process")

    def getResultsQ(self):
        """Information is passed from the child process back to the main process through this queue."""
        return self._resultQ


class RoiSaverController(QObject):
    """Instantiating this class begins the process of saving a ROI. This class handles the GUI related stuff in the main thread."""
    def open(self):
        self.worker.start()  # Start a process that saves ROIS
        self.thread.start() # Start the thread that reads the results queue from the thread and translates it into Qt signals that trigger GUI events

    def close(self):
        self.worker.requestClose()
        # We used to have a `join` here to make sure that the process actually closed, it was a bit slow and froze up the GUI for > 1second

    def saveNewRoi(self, name: str, num: int, verts, datashape, acq: AcqDir):
        self.placeHolderPoly = patches.Polygon(verts, facecolor=(0, .5, 0.5, 0.4)) #this is a temporary polygon display until the ROI file is actually ready to be read.
        self.anViewer.ax.add_patch(self.placeHolderPoly)
        self.worker.saveNewRoi(name, num, verts, datashape, acq) # Place the saving information in a queue to be saved in a separate process, this avoids freezing up the GUI.
        self.anViewer.canvas.draw_idle()

    def __init__(self, anViewer, parent: QWidget):
        """This initializer starts a separate thread and runs RoiSaverWorker.doWork on that thread. GUI related work is linked to the appropriate
        signals from the other thread. This multithreaded approach turns out to be mostly pointless. Because of pythons GIL the roid drawing still becomes
        temporarily frozen while the ROI is saved. It seems the only way to make this faster is to optimize the saving operation."""
        super().__init__(parent)
        self.anViewer = anViewer  #A reference to an analysis viewer widget that we draw ROI's on.
        self.worker = _RoiSaverProcess()  # A process that saves ROI's without blocking the GUI thread.
        self.thread = QThread()  # This thread will be used to run the qChecker object.
        self.qChecker = _QueueCheckerThread(self.worker.getResultsQ())  # This object runs a blocking function in a separate thread that fires Qt signals based on values returned from the saving process.
        self.thread.setObjectName('QueueCheckerThread')
        self.qChecker.moveToThread(self.thread)  # If qChecker has a parent widget then this will fail.
        self.thread.started.connect(self.qChecker.doWork)  # We can't call the function directly, we need to use a QT signal so it runs in the other thread.
        self.qChecker.roiFinished.connect(self._drawSavedRoi)
        self.qChecker.roiNeedsOverwrite.connect(self._overWriteRoi)

    def _overWriteRoi(self, acq: AcqDir, roi: Roi):
        """If the worker raised an `OSError` then we need to ask the user if they want to overwrite. This must be done in the main thread."""
        ans = QMessageBox.question(self.anViewer, 'Overwrite?', f"Roi {roi.name}:{roi.number} already exists. Overwrite?")
        if ans == QMessageBox.Yes:
            acq.saveRoi(roi, overwrite=True)
            self.anViewer.showRois() #Refresh all rois since we just deleted one as well.
            self._roiIsSaved()
        self._finish()

    def _drawSavedRoi(self, roi: Roi):
        """The worker signals that it successfully save the roi, now display it."""
        self.anViewer.addRoi(roi)
        self._roiIsSaved()
        self._finish()

    def _roiIsSaved(self):
        """Either way, once a  new roi has been saved we want to do this."""
        QApplication.instance().window.cellSelector.refreshCellItems()  # Refresh the cell selection table.

    def _finish(self):
        """Even if the roi wasn't ultimately saved we want to do this."""
        self.placeHolderPoly.remove()
        self.anViewer.canvas.draw_idle()