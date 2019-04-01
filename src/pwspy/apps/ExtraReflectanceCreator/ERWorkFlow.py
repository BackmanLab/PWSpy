import os
from glob import glob
from typing import List

from pwspy import ImCube, CameraCorrection
from pwspy.utility import loadAndProcess
from .extraReflectance import prepareData, plotExtraReflection, saveRExtra
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt

class ERWorkFlow:
    def __init__(self):
        self.meanValues=self.allCombos=self.theoryR=self.matCombos=self.settings=None

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
    def _processIm(im: ImCube, camCorrection: CameraCorrection) -> ImCube:
        im.correctCameraEffects(camCorrection)
        im.normalizeByExposure()
        im.filterDust(6)  # TODO change units
        return im

    def loadDirectory(self, directory: str):
        self.directory = directory
        files = glob(os.path.join(directory, '*', '*', 'Cell*'))
        fileDict = {}
        for file in files:
            filelist = self._splitPath(file)
            s = filelist[2]
            m = filelist[1]
            if m not in fileDict: fileDict[m] = {}
            if s not in fileDict[m]: fileDict[m][s] = []
            fileDict[m][s].append(file)
        cubes = loadAndProcess(fileDict, self._processIm, specifierNames=['material', 'setting'], parallel=True, procArgs=[cameraCorrection])
        self.meanValues, self.allCombos, self.theoryR, self.matCombos, self.settings = prepareData(cubes)

    def plot(self, saveToPdf: bool):
        plotExtraReflection(self.allCombos, self.meanValues, self.theoryR, self.matCombos, self.settings)
        with PdfPages(os.path.join(self.directory, "figs.pdf")) as pp:
            for i in plt.get_fignums():
                f = plt.figure(i)
                f.set_size_inches(9,9)
                pp.savefig(f)