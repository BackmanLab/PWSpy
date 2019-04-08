import os
from glob import glob
from typing import List
import json
from pwspy import ImCube, CameraCorrection
from pwspy.utility import loadAndProcess
from .extraReflectance import prepareData, plotExtraReflection, saveRExtra
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd


class ERWorkFlow:
    def __init__(self):
        self.meanValues=self.allCombos=self.theoryR=self.matCombos=self.settings=self.directory=self.cameraCorrection=None

    @staticmethod
    def _splitPath(path: str) -> List[str]:
        folders = []
        while 1:
            path, folder = os.path.split(path)
            if folder != "":
                folders.append(folder)
            else:
                if path != "":
                    folders.append(path)
                break
        return folders

    @staticmethod
    def _processIm(im: ImCube, camCorrection: CameraCorrection, binning: int) -> ImCube:
        im.correctCameraEffects(camCorrection, binning=binning)
        im.normalizeByExposure()
        im.filterDust(6)  # TODO change units
        return im

    def getDirectorySettings(self, directory: str) -> List[str]:
        files = glob(os.path.join(directory, '*'))
        settings = [os.path.split(file)[-1] for file in files if os.path.isdir(file)]
        return settings

    def loadDirectory(self, directory: str, includeSettings: List[str], binning: int):
        self.directory = directory
        # Check for a cameraCorrection
        self.cameraCorrection = CameraCorrection.fromJsonFile(os.path.join(self.directory, 'cameraCorrection.json'))
        # Generate the fileDict
        files = glob(os.path.join(directory, '*', '*', 'Cell*'))
        rows = []
        for file in files:
            filelist = self._splitPath(file)
            s = filelist[2]
            m = filelist[1]
            if s in includeSettings:
                rows.append({'setting': s, 'material': m, 'cube': file})
        df = pd.DataFrame(rows)
        cubes = loadAndProcess(df, self._processIm, parallel=True, procArgs=[self.cameraCorrection, binning])
        self.meanValues, self.allCombos, self.theoryR, self.matCombos, self.settings = prepareData(cubes)

    def plot(self, saveToPdf: bool = False):
        plotExtraReflection(self.allCombos, self.meanValues, self.theoryR, self.matCombos, self.settings)
        if saveToPdf:
            with PdfPages(os.path.join(self.directory, "figs.pdf")) as pp:
                for i in plt.get_fignums():
                    f = plt.figure(i)
                    f.set_size_inches(9, 9)
                    pp.savefig(f)

    def save(self):
        pass

    def compareDates(self):
        pass