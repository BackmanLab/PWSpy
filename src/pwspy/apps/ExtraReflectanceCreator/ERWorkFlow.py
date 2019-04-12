import os
from glob import glob
from typing import List, Any, Dict
import json
from pwspy import ImCube, CameraCorrection, ExtraReflectanceCube
from pwspy.utility import loadAndProcess
from pwspy.utility.reflectanceHelper import Material
import pwspy.apps.ExtraReflectanceCreator.extraReflectance  as er #import prepareData, plotExtraReflection, saveRExtra
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib import animation
import traceback

class ERWorkFlow:
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

    @staticmethod
    def scanDirectory(directory: str) -> Dict[str, Any]:
        try:
            cam = CameraCorrection.fromJsonFile(os.path.join(directory, 'cameraCorrection.json'))
        except Exception as e:
            print(e)
            raise Exception(f"Could not load a camera correction at {directory}")
        files = glob(os.path.join(directory, '*', '*', 'Cell*'))
        rows = []
        matMap = {'air': Material.Air, 'water': Material.Water, 'ipa': Material.Ipa, 'ethanol': Material.Ethanol}
        for file in files:
            filelist = ERWorkFlow._splitPath(file)
            s = filelist[2]
            m = matMap[filelist[1]]
            rows.append({'setting': s, 'material': m, 'cube': file})
        df = pd.DataFrame(rows)
        return {'dataFrame': df, 'camCorrection': cam}

    @staticmethod
    def loadCubes(df: pd.DataFrame, includeSettings: List[str], binning: int, cameraCorrection: CameraCorrection):
        df = df[df['setting'].isin(includeSettings)]
        cubes = loadAndProcess(df, ERWorkFlow._processIm, parallel=True, procArgs=[cameraCorrection, binning])
        return cubes

    @staticmethod
    def plot(cubes: pd.DataFrame, saveToPdf: bool = False, saveDir: str = None):
        settings = set(cubes['setting'])  # Unique setting values
        materials = set(cubes['material'])
        theoryR = er.getTheoreticalReflectances(materials, cubes['cube'][0].wavelengths)  # Theoretical reflectances
        matCombos = er.generateMaterialCombos(materials)

        print("Select an ROI")
        mask = cubes['cube'].sample(n=1).iloc[0].selectLassoROI()  # Select an ROI to analyze
        er.plotExtraReflection(cubes, theoryR, matCombos, mask)
        if saveToPdf:
            with PdfPages(os.path.join(saveDir, "figs.pdf")) as pp:
                for i in plt.get_fignums():
                    f = plt.figure(i)
                    f.set_size_inches(9, 9)
                    pp.savefig(f)

    @staticmethod
    def save(cubes: pd.DataFrame, saveDir: str, saveName: str):
        settings = set(cubes['setting'])
        materials = set(cubes['material'])
        assert len(settings) == 1
        theoryR = er.getTheoreticalReflectances(materials, cubes['cube'][0].wavelengths)  # Theoretical reflectances
        matCombos = er.generateMaterialCombos(materials)
        combos = er.getAllCubeCombos(matCombos, cubes)
        erCube, rExtraDict = er.generateRExtraCubes(combos, theoryR)
        erCube.toHdfFile(saveDir, saveName)

    @staticmethod
    def compareDates(cubes: pd.DataFrame):
        er.compareDates(cubes)
