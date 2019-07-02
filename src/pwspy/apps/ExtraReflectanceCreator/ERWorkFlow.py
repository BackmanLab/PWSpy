import hashlib
import os
from datetime import datetime
from glob import glob
from typing import List, Any, Dict
import json
from pwspy.imCube import ImCube, CameraCorrection, ExtraReflectanceCube
from pwspy.apps.ExtraReflectanceCreator.widgets.dialog import IndexInfoForm
from pwspy.imCube import ICMetaData
from pwspy.imCube.otherClasses import Roi
from pwspy.moduleConsts import dateTimeFormat, Material
from pwspy.utility.io import loadAndProcess
import pwspy.apps.ExtraReflectanceCreator.extraReflectance  as er
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.pyplot as plt
import pandas as pd

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
    matMap = {'air': Material.Air, 'water': Material.Water, 'ipa': Material.Ipa, 'ethanol': Material.Ethanol, 'glass': Material.Glass}
    for file in files:
        filelist = _splitPath(file)
        s = filelist[2]
        m = matMap[filelist[1]]
        rows.append({'setting': s, 'material': m, 'cube': file})
    df = pd.DataFrame(rows)
    return {'dataFrame': df, 'camCorrection': cam}


def _processIm(im: ImCube, args) -> ImCube:
    im.correctCameraEffects(**args)
    im.normalizeByExposure()
    try:
        im.filterDust(0.8)  # in microns
    except ValueError:
        print("No pixel size metadata found. assuming a gaussian filter radius of 6 pixels = 1 sigma.")
        im.filterDust(6, pixelSize=1) #Do the filtering in units of pixels if no auto pixelsize was found
    return im

class ERWorkFlow:
    def __init__(self, workingDir: str, homeDir: str):
        self.cubes = self.fileStruct = self.df = self.cameraCorrection = self.currDir = self.plotnds = self.anims = None
        self.figs = []
        self.homeDir = homeDir
        # generateFileStruct:
        folders = [i for i in glob(os.path.join(workingDir, '*')) if os.path.isdir(i)]
        settings = [os.path.split(i)[-1] for i in folders]
        fileStruct = {}
        for f, s in zip(folders, settings):
            fileStruct[s] = scanDirectory(f)
        self.fileStruct = fileStruct

    def invalidateCubes(self):
        self.cubes = None

    def deleteFigures(self):
        for fig in self.figs:
            plt.close(fig)
        self.figs = []

    def loadCubes(self, includeSettings: List[str], binning: int):
        df = self.df[self.df['setting'].isin(includeSettings)]
        if binning is None:
            args = {'correction': None, 'binning': None, 'auto': True}
            for cube in df['cube']:
                md = ICMetaData.loadAny(cube)
                if md.binning is None:
                    raise Exception("No binning metadata found. Please specify a binning setting.")
                elif md.cameraCorrection is None:
                    raise Exception("No camera correction metadata found. Please specify a binning setting, in this case the application will use the camera correction stored in the cameraCorrection.json file of the calibration folder")
        else:
            args = {'correction': self.cameraCorrection, 'binning': binning, 'auto': False}
        self.cubes = loadAndProcess(df, _processIm, parallel=True, procArgs=[args])

    def plot(self, saveToPdf: bool = False, saveDir: str = None):
        cubes = self.cubes
        settings = set(cubes['setting'])  # Unique setting values
        materials = set(cubes['material'])
        theoryR = er.getTheoreticalReflectances(materials, cubes['cube'].iloc[0].wavelengths)  # Theoretical reflectances
        matCombos = er.generateMaterialCombos(materials)

        print("Select an ROI")
        verts = cubes['cube'].sample(n=1).iloc[0].selectLassoROI()  # Select an ROI to analyze
        mask = Roi.fromVerts('doesntmatter', 1, verts, cubes['cube'].sample(n=1).iloc[0].data.shape[:-1])
        self.figs.extend(er.plotExtraReflection(cubes, theoryR, matCombos, mask, plotReflectionImages=True))
        if saveToPdf:
            with PdfPages(os.path.join(saveDir, f"fig_{datetime.strftime(datetime.now(), dateTimeFormat)}.pdf")) as pp:
                for i in plt.get_fignums():
                    f = plt.figure(i)
                    f.set_size_inches(9, 9)
                    pp.savefig(f)

    def save(self):
        settings = set(self.cubes['setting'])
        for setting in settings:
            cubes = self.cubes[self.cubes['setting'] == setting]
            materials = set(cubes['material'])
            theoryR = er.getTheoreticalReflectances(materials, cubes['cube'].iloc[0].wavelengths)  # Theoretical reflectances
            matCombos = er.generateMaterialCombos(materials)
            combos = er.getAllCubeCombos(matCombos, cubes)
            erCube, rExtraDict, self.plotnds = er.generateRExtraCubes(combos, theoryR)
            print(f"Final data max is {erCube.data.max()}")
            print(f"Final data min is {erCube.data.min()}")
            self.figs.extend([i.fig for i in self.plotnds]) # keep track of opened figures.
            saveName = f'{self.currDir}-{setting}'
            dialog = IndexInfoForm(f'{self.currDir}-{setting}', erCube.metadata.idTag)
            dialog.exec()
            erCube.metadata.inheritedMetadata['description'] = dialog.description
            erCube.toHdfFile(self.homeDir, saveName)
            self.updateIndex(saveName, erCube.metadata.idTag, dialog.description, erCube.metadata.dirName2Directory('', saveName))

    def updateIndex(self, saveName: str, idTag: str, description: str, filePath: str):
        with open(os.path.join(self.homeDir, 'index.json'), 'r') as f:
            index = json.load(f)
        md5hash = hashlib.md5()
        with open(os.path.join(self.homeDir, filePath), 'rb') as f:
            md5hash.update(f.read())
        md5 = md5hash.hexdigest() #The md5 checksum as a string of hex.
        cubes = index['reflectanceCubes']
        newEntry = {'fileName': filePath,
                    'description': description,
                    'idTag': idTag,
                    'name': saveName,
                    'md5': md5}
        cubes.append(newEntry)
        index['reflectanceCubes'] = cubes
        index['creationDate'] = datetime.strftime(datetime.now(), dateTimeFormat)
        with open(os.path.join(self.homeDir, 'index.json'), 'w') as f:
            json.dump(index, f, indent=4)

    def compareDates(self):
        self.anims, figs = er.compareDates(self.cubes) #The animation objects must not be deleted for the animations to keep working
        self.figs.extend(figs) #Keep track of opened figures.

    def directoryChanged(self, directory: str):
        self.currDir = directory
        _ = self.fileStruct[directory]
        self.df = _['dataFrame']
        self.cameraCorrection = _['camCorrection']
        self.invalidateCubes()
