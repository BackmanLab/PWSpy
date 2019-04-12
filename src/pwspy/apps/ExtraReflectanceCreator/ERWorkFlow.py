import os
from glob import glob
from typing import List, Any, Dict
import json
from pwspy import ImCube, CameraCorrection, ExtraReflectanceCube
from pwspy.imCube import ICMetaData
from pwspy.utility import loadAndProcess
from pwspy.utility.reflectanceHelper import Material
import pwspy.apps.ExtraReflectanceCreator.extraReflectance  as er #import prepareData, plotExtraReflection, saveRExtra
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib import animation

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
        filelist = _splitPath(file)
        s = filelist[2]
        m = matMap[filelist[1]]
        rows.append({'setting': s, 'material': m, 'cube': file})
    df = pd.DataFrame(rows)
    return {'dataFrame': df, 'camCorrection': cam}

def _processIm(im: ImCube, camCorrection: CameraCorrection, binning: int) -> ImCube:
    im.correctCameraEffects(camCorrection, binning=binning)
    im.normalizeByExposure()
    im.filterDust(6)  # TODO change units
    return im

class ERWorkFlow:
    def __init__(self):
        self.cubes = self.fileStruct = None

    def generateFileStruct(self, workingDir: str):
            folders = [i for i in glob(os.path.join(workingDir, '*')) if os.path.isdir(i)]
            settings = [os.path.split(i)[-1] for i in folders]
            fileStruct = {}
            for f, s in zip(folders, settings):
                fileStruct[s] = scanDirectory(f)
            self.fileStruct = fileStruct

    def invalidateCubes(self):
        self.cubes = None

    def loadCubes(self, includeSettings: List[str], binning: int):
        if binning is None:
            md = ICMetaData.loadAny(self.df['cube'].loc[0])
            if 'binning' not in md.metadata:
                raise Exception("No binning metadata found. Please specify a binning setting.")
        df = self.df[self.df['setting'].isin(includeSettings)]
        self.cubes = loadAndProcess(df, _processIm, parallel=True, procArgs=[self.cameraCorrection, binning])

    def plot(self, saveToPdf: bool = False, saveDir: str = None):
        cubes = self.cubes
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

    def save(self, saveDir: str, saveName: str):
        settings = set(self.cubes['setting'])
        for setting in settings:
            cubes = self.cubes[self.cubes['setting'] == setting]
            materials = set(cubes['material'])
            theoryR = er.getTheoreticalReflectances(materials, cubes['cube'][0].wavelengths)  # Theoretical reflectances
            matCombos = er.generateMaterialCombos(materials)
            combos = er.getAllCubeCombos(matCombos, cubes)
            erCube, rExtraDict = er.generateRExtraCubes(combos, theoryR)
            erCube.toHdfFile(saveDir, saveName)

    def compareDates(self):
        self.anims = er.compareDates(self.cubes) #The animation objects must not be deleted for the animations to keep working

    def selectionChanged(self, directory: str):
        _ = self.fileStruct[directory]
        self.df = _['dataFrame']
        self.cameraCorrection = _['camCorrection']
        self.invalidateCubes()
